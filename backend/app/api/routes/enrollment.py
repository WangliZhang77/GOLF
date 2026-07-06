from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enrollment import EnrollmentStatus, TeamEnrollment
from app.models.team import Team
from app.models.user import User, UserRole
from app.schemas.enrollment import EnrollmentApply, EnrollmentOut, EnrollmentReview

router = APIRouter(prefix="/org/enrollments", tags=["enrollment"])

_ACTIVE_STATUSES = (EnrollmentStatus.pending_captain, EnrollmentStatus.pending_branch)


def _get_team(db: Session, team_id: int) -> Team:
    team = db.query(Team).filter(Team.id == team_id, Team.is_deleted.is_(False)).first()
    if team is None:
        raise HTTPException(status_code=404, detail="球队不存在 / Team not found")
    return team


@router.post("/apply", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
def apply_enrollment(
    payload: EnrollmentApply,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_team(db, payload.team_id)

    existing = (
        db.query(TeamEnrollment)
        .filter(
            TeamEnrollment.team_id == payload.team_id,
            TeamEnrollment.user_id == current_user.id,
            TeamEnrollment.status.in_(_ACTIVE_STATUSES),
            TeamEnrollment.is_deleted.is_(False),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="已有进行中的入队申请 / Pending application exists",
        )

    enr = TeamEnrollment(
        team_id=payload.team_id,
        user_id=current_user.id,
        status=EnrollmentStatus.pending_captain,
        remark=payload.remark,
        created_by=current_user.id,
    )
    db.add(enr)
    db.commit()
    db.refresh(enr)
    return enr


@router.get("", response_model=list[EnrollmentOut])
def list_enrollments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(TeamEnrollment).filter(TeamEnrollment.is_deleted.is_(False))

    if current_user.role == UserRole.super_admin:
        pass
    elif current_user.role == UserRole.council_admin and current_user.branch_id:
        team_ids = [
            t.id
            for t in db.query(Team.id)
            .filter(Team.branch_id == current_user.branch_id)
            .all()
        ]
        query = query.filter(TeamEnrollment.team_id.in_(team_ids or [-1]))
    elif current_user.role == UserRole.team_captain:
        team_ids = [
            t.id
            for t in db.query(Team.id)
            .filter(Team.captain_id == current_user.id)
            .all()
        ]
        query = query.filter(TeamEnrollment.team_id.in_(team_ids or [-1]))
    else:
        query = query.filter(TeamEnrollment.user_id == current_user.id)

    return query.order_by(TeamEnrollment.id.desc()).all()


def _get_enrollment(db: Session, enrollment_id: int) -> TeamEnrollment:
    enr = (
        db.query(TeamEnrollment)
        .filter(
            TeamEnrollment.id == enrollment_id, TeamEnrollment.is_deleted.is_(False)
        )
        .first()
    )
    if enr is None:
        raise HTTPException(status_code=404, detail="申请不存在 / Not found")
    return enr


@router.post("/{enrollment_id}/captain-review", response_model=EnrollmentOut)
def captain_review(
    enrollment_id: int,
    payload: EnrollmentReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enr = _get_enrollment(db, enrollment_id)
    team = _get_team(db, enr.team_id)

    is_super = current_user.role == UserRole.super_admin
    is_captain = (
        current_user.role == UserRole.team_captain and team.captain_id == current_user.id
    )
    if not (is_super or is_captain):
        raise HTTPException(status_code=403, detail="仅队长可审核 / Captain only")

    if enr.status != EnrollmentStatus.pending_captain:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前状态不可队长审核 / Invalid state",
        )

    enr.captain_reviewed_by = current_user.id
    enr.captain_reviewed_at = datetime.now(timezone.utc)
    enr.updated_by = current_user.id
    if payload.approve:
        enr.status = EnrollmentStatus.pending_branch
    else:
        enr.status = EnrollmentStatus.rejected
    if payload.remark:
        enr.remark = payload.remark
    db.commit()
    db.refresh(enr)
    return enr


@router.post("/{enrollment_id}/branch-review", response_model=EnrollmentOut)
def branch_review(
    enrollment_id: int,
    payload: EnrollmentReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enr = _get_enrollment(db, enrollment_id)
    team = _get_team(db, enr.team_id)

    is_super = current_user.role == UserRole.super_admin
    is_branch_admin = (
        current_user.role == UserRole.council_admin
        and current_user.branch_id == team.branch_id
    )
    if not (is_super or is_branch_admin):
        raise HTTPException(status_code=403, detail="仅分会理事可备案 / Branch admin only")

    if enr.status != EnrollmentStatus.pending_branch:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前状态不可分会备案 / Invalid state",
        )

    enr.branch_reviewed_by = current_user.id
    enr.branch_reviewed_at = datetime.now(timezone.utc)
    enr.updated_by = current_user.id
    if payload.approve:
        enr.status = EnrollmentStatus.approved
        # 备案通过：将申请人主队设为该球队
        applicant = db.query(User).filter(User.id == enr.user_id).first()
        if applicant:
            applicant.team_id = team.id
            applicant.branch_id = team.branch_id
    else:
        enr.status = EnrollmentStatus.rejected
    if payload.remark:
        enr.remark = payload.remark
    db.commit()
    db.refresh(enr)
    return enr
