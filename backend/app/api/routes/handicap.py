from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.handicap import HandicapHistory, HandicapSource
from app.models.member import Member
from app.models.user import User, UserRole
from app.schemas.handicap import HandicapAdjustRequest, HandicapDashboardOut
from app.services.handicap import compute_trend

router = APIRouter(prefix="/handicap", tags=["handicap"])

_MANAGE_ROLES = {UserRole.super_admin, UserRole.council_admin}


def _get_member_for_user(db: Session, user: User) -> Member:
    m = (
        db.query(Member)
        .filter(Member.user_id == user.id, Member.is_deleted.is_(False))
        .first()
    )
    if m is None:
        raise HTTPException(status_code=404, detail="尚未建立会员档案 / No member profile")
    return m


def _get_member(db: Session, member_id: int) -> Member:
    m = (
        db.query(Member)
        .filter(Member.id == member_id, Member.is_deleted.is_(False))
        .first()
    )
    if m is None:
        raise HTTPException(status_code=404, detail="会员不存在 / Member not found")
    return m


def _assert_manage_scope(member: Member, user: User) -> None:
    if user.role == UserRole.super_admin:
        return
    if user.role == UserRole.council_admin and user.branch_id == member.branch_id:
        return
    raise HTTPException(status_code=403, detail="权限不足 / Forbidden")


def _dashboard(db: Session, member: Member) -> HandicapDashboardOut:
    history = (
        db.query(HandicapHistory)
        .filter(HandicapHistory.member_id == member.id, HandicapHistory.is_deleted.is_(False))
        .order_by(HandicapHistory.date, HandicapHistory.id)
        .all()
    )
    trend = compute_trend(history, member.handicap)
    return HandicapDashboardOut(
        member_id=member.id,
        current_handicap=member.handicap,
        trend=trend,
        history=list(reversed(history)),
    )


@router.get("/me", response_model=HandicapDashboardOut)
def my_handicap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    member = _get_member_for_user(db, current_user)
    return _dashboard(db, member)


@router.get("/members/{member_id}", response_model=HandicapDashboardOut)
def member_handicap(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    member = _get_member(db, member_id)
    _assert_manage_scope(member, current_user)
    return _dashboard(db, member)


@router.patch("/members/{member_id}", response_model=HandicapDashboardOut)
def adjust_handicap(
    member_id: int,
    payload: HandicapAdjustRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    member = _get_member(db, member_id)
    _assert_manage_scope(member, current_user)

    db.add(
        HandicapHistory(
            member_id=member.id,
            date=date.today(),
            old_handicap=member.handicap,
            new_handicap=payload.new_handicap,
            source=HandicapSource.manual,
            remark=payload.remark,
            created_by=current_user.id,
        )
    )
    member.handicap = payload.new_handicap
    member.updated_by = current_user.id
    db.commit()
    db.refresh(member)
    return _dashboard(db, member)
