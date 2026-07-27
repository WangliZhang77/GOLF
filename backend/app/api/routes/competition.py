from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.competition import (
    Competition,
    CompetitionRegApprovalStatus,
    CompetitionRegistration,
    CompetitionRegPaymentStatus,
    CompetitionStatus,
)
from app.models.member import Member, MemberLevel, MemberStatus
from app.models.user import User, UserRole
from app.schemas.competition import (
    CompetitionApprovalRequest,
    CompetitionCreate,
    CompetitionOut,
    CompetitionRegisterRequest,
    CompetitionRegistrationOut,
    CompetitionUpdate,
)
from app.services.billing import member_has_outstanding

router = APIRouter(prefix="/competitions", tags=["competition"])

_MANAGE_ROLES = {
    UserRole.super_admin,
    UserRole.council_admin,
    UserRole.event_director,
}
# 报名占坑状态：待审 + 已通过都占名额（提交即预留），拒绝不占坑
_HELD_APPROVAL = (
    CompetitionRegApprovalStatus.pending,
    CompetitionRegApprovalStatus.approved,
)


def _as_aware_utc(dt: datetime) -> datetime:
    """SQLite（测试环境）不保留 tzinfo，取回的 timezone=True 列会是 naive；
    统一按 UTC 补齐，避免与 aware 的 now() 比较时报错。"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _get_competition(db: Session, competition_id: int) -> Competition:
    c = (
        db.query(Competition)
        .filter(Competition.id == competition_id, Competition.is_deleted.is_(False))
        .first()
    )
    if c is None:
        raise HTTPException(status_code=404, detail="赛事不存在 / Competition not found")
    return c


def _assert_competition_manage(competition: Competition, user: User, db: Session) -> None:
    if user.role in {UserRole.super_admin, UserRole.event_director}:
        return
    if (
        user.role == UserRole.council_admin
        and competition.branch_id is not None
        and user.branch_id == competition.branch_id
    ):
        return
    raise HTTPException(status_code=403, detail="权限不足 / Forbidden")


def _competition_query_for_user(db: Session, user: User):
    q = db.query(Competition).filter(Competition.is_deleted.is_(False))
    if user.role in {UserRole.super_admin, UserRole.finance, UserRole.event_director}:
        return q
    if user.role == UserRole.council_admin and user.branch_id:
        return q.filter(
            (Competition.branch_id == user.branch_id) | (Competition.branch_id.is_(None))
        )
    # 队长/普通会员：仅可见非草稿赛事
    return q.filter(Competition.status != CompetitionStatus.draft)


def _counts(db: Session, competition_id: int) -> dict[str, int]:
    base = db.query(CompetitionRegistration).filter(
        CompetitionRegistration.competition_id == competition_id,
        CompetitionRegistration.is_deleted.is_(False),
    )
    registered = base.filter(
        CompetitionRegistration.approval_status.in_(_HELD_APPROVAL)
    ).count()
    approved = base.filter(
        CompetitionRegistration.approval_status == CompetitionRegApprovalStatus.approved
    ).count()
    return {"registered_count": registered, "approved_count": approved}


def _get_member_for_user(db: Session, user: User) -> Member:
    m = (
        db.query(Member)
        .filter(Member.user_id == user.id, Member.is_deleted.is_(False))
        .first()
    )
    if m is None:
        raise HTTPException(status_code=404, detail="尚未建立会员档案 / No member profile")
    return m


def _my_registration_status(
    db: Session, competition_id: int, user: User
) -> CompetitionRegApprovalStatus | None:
    member = (
        db.query(Member)
        .filter(Member.user_id == user.id, Member.is_deleted.is_(False))
        .first()
    )
    if member is None:
        return None
    reg = (
        db.query(CompetitionRegistration)
        .filter(
            CompetitionRegistration.competition_id == competition_id,
            CompetitionRegistration.member_id == member.id,
            CompetitionRegistration.approval_status.in_(_HELD_APPROVAL),
            CompetitionRegistration.is_deleted.is_(False),
        )
        .order_by(CompetitionRegistration.id.desc())
        .first()
    )
    return reg.approval_status if reg else None


def _to_out(db: Session, competition: Competition, current_user: User) -> CompetitionOut:
    data = CompetitionOut.model_validate(competition).model_dump()
    data.update(_counts(db, competition.id))
    if current_user.role == UserRole.member:
        data["my_registration_status"] = _my_registration_status(
            db, competition.id, current_user
        )
    return CompetitionOut(**data)


@router.post("", response_model=CompetitionOut, status_code=status.HTTP_201_CREATED)
def create_competition(
    payload: CompetitionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    if current_user.role == UserRole.council_admin:
        if payload.branch_id is None or payload.branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=403, detail="只能创建本分会赛事 / Own branch only"
            )
    competition = Competition(**payload.model_dump(), created_by=current_user.id)
    db.add(competition)
    db.commit()
    db.refresh(competition)
    return _to_out(db, competition, current_user)


@router.get("", response_model=list[CompetitionOut])
def list_competitions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    competitions = (
        _competition_query_for_user(db, current_user)
        .order_by(Competition.start_time.desc())
        .all()
    )
    return [_to_out(db, c, current_user) for c in competitions]


@router.get("/{competition_id}", response_model=CompetitionOut)
def get_competition(
    competition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    competition = _get_competition(db, competition_id)
    if (
        current_user.role in {UserRole.member, UserRole.team_captain}
        and competition.status == CompetitionStatus.draft
    ):
        raise HTTPException(status_code=404, detail="赛事不存在 / Competition not found")
    return _to_out(db, competition, current_user)


@router.put("/{competition_id}", response_model=CompetitionOut)
def update_competition(
    competition_id: int,
    payload: CompetitionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(competition, field, value)
    competition.updated_by = current_user.id
    db.commit()
    db.refresh(competition)
    return _to_out(db, competition, current_user)


@router.post("/{competition_id}/publish", response_model=CompetitionOut)
def publish_competition(
    competition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user, db)
    competition.status = CompetitionStatus.open
    competition.updated_by = current_user.id
    db.commit()
    db.refresh(competition)
    return _to_out(db, competition, current_user)


@router.post(
    "/{competition_id}/register",
    response_model=CompetitionRegistrationOut,
    status_code=status.HTTP_201_CREATED,
)
def register_competition(
    competition_id: int,
    payload: CompetitionRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    competition = _get_competition(db, competition_id)
    if competition.status != CompetitionStatus.open:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="赛事未开放报名 / Registration closed",
        )
    if (
        competition.registration_deadline
        and datetime.now(timezone.utc) > _as_aware_utc(competition.registration_deadline)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="报名已截止 / Registration deadline passed",
        )

    member = _get_member_for_user(db, current_user)
    if member.level == MemberLevel.blacklist:
        raise HTTPException(status_code=403, detail="黑名单会员不可报名 / Blacklisted")
    if member.status != MemberStatus.active:
        raise HTTPException(status_code=403, detail="会员状态不可报名 / Inactive member")
    if member_has_outstanding(db, member.id):
        raise HTTPException(
            status_code=403,
            detail="存在未缴清费用，请先结清后再报名 / Outstanding dues must be settled before registering",
        )

    if competition.max_handicap is not None:
        if member.handicap is None:
            raise HTTPException(
                status_code=403,
                detail=(
                    "差点信息缺失，无法核实报名资格，请先完善差点后再报名 / "
                    "Handicap not on file — cannot verify eligibility, please update your handicap before registering"
                ),
            )
        if member.handicap > competition.max_handicap:
            raise HTTPException(
                status_code=403,
                detail="差点超过本赛事上限 / Handicap exceeds competition limit",
            )

    existing = (
        db.query(CompetitionRegistration)
        .filter(
            CompetitionRegistration.competition_id == competition_id,
            CompetitionRegistration.member_id == member.id,
            CompetitionRegistration.approval_status.in_(_HELD_APPROVAL),
            CompetitionRegistration.is_deleted.is_(False),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="已报名 / Already registered"
        )

    held_count = (
        db.query(CompetitionRegistration)
        .filter(
            CompetitionRegistration.competition_id == competition_id,
            CompetitionRegistration.approval_status.in_(_HELD_APPROVAL),
            CompetitionRegistration.is_deleted.is_(False),
        )
        .count()
    )
    if held_count >= competition.max_players:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="名额已满 / Slots full"
        )

    reg = CompetitionRegistration(
        competition_id=competition_id,
        member_id=member.id,
        user_id=current_user.id,
        team_id=member.team_id,
        payment_status=CompetitionRegPaymentStatus.unpaid,
        approval_status=CompetitionRegApprovalStatus.pending,
        remark=payload.remark,
        created_by=current_user.id,
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)
    return reg


@router.get(
    "/{competition_id}/registrations", response_model=list[CompetitionRegistrationOut]
)
def list_registrations(
    competition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user, db)
    return (
        db.query(CompetitionRegistration)
        .filter(
            CompetitionRegistration.competition_id == competition_id,
            CompetitionRegistration.is_deleted.is_(False),
        )
        .order_by(CompetitionRegistration.id)
        .all()
    )


@router.post(
    "/{competition_id}/registrations/{reg_id}/approve",
    response_model=CompetitionRegistrationOut,
)
def approve_registration(
    competition_id: int,
    reg_id: int,
    payload: CompetitionApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user, db)
    reg = (
        db.query(CompetitionRegistration)
        .filter(
            CompetitionRegistration.id == reg_id,
            CompetitionRegistration.competition_id == competition_id,
            CompetitionRegistration.is_deleted.is_(False),
        )
        .first()
    )
    if reg is None:
        raise HTTPException(status_code=404, detail="报名不存在 / Not found")

    reg.approval_status = (
        CompetitionRegApprovalStatus.approved
        if payload.approve
        else CompetitionRegApprovalStatus.rejected
    )
    if payload.remark is not None:
        reg.remark = payload.remark
    reg.updated_by = current_user.id
    db.commit()
    db.refresh(reg)
    return reg


@router.get("/{competition_id}/my-registration", response_model=CompetitionRegistrationOut)
def my_registration(
    competition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_competition(db, competition_id)
    member = _get_member_for_user(db, current_user)
    reg = (
        db.query(CompetitionRegistration)
        .filter(
            CompetitionRegistration.competition_id == competition_id,
            CompetitionRegistration.member_id == member.id,
            CompetitionRegistration.is_deleted.is_(False),
        )
        .order_by(CompetitionRegistration.id.desc())
        .first()
    )
    if reg is None:
        raise HTTPException(status_code=404, detail="未找到报名记录 / No registration found")
    return reg
