from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.core.security import hash_password
from app.models.member import Member, MemberLevel, MemberStatus
from app.models.team import Team
from app.models.user import User, UserRole
from app.services.attendance import PROMOTE_MIN_ATTENDANCE, count_member_checkins
from app.services.billing import member_has_outstanding
from app.schemas.member import (
    MemberAdminUpdate,
    MemberCreate,
    MemberFullOut,
    MemberPublicOut,
    MemberSelfUpdate,
    PromoteResult,
)

router = APIRouter(prefix="/members", tags=["member"])

# 可查看隐私信息的角色
_PRIVILEGED_ROLES = {UserRole.super_admin, UserRole.finance}
# 转正门槛（月数近似为天数；出勤/欠费校验在 Phase 4/5 补充）
_PROMOTE_MIN_DAYS = 90
_SLEEP_DAYS = 365


def _serialize(member: Member, viewer: User):
    can_see_private = (
        viewer.role in _PRIVILEGED_ROLES or member.user_id == viewer.id
    )
    if can_see_private:
        return MemberFullOut.model_validate(member)
    return MemberPublicOut.model_validate(member)


def _get_member(db: Session, member_id: int) -> Member:
    m = (
        db.query(Member)
        .filter(Member.id == member_id, Member.is_deleted.is_(False))
        .first()
    )
    if m is None:
        raise HTTPException(status_code=404, detail="会员不存在 / Member not found")
    return m


def _own_team_ids(db: Session, user: User) -> list[int]:
    return [
        t.id
        for t in db.query(Team.id).filter(Team.captain_id == user.id).all()
    ]


def _assert_manage_scope(member: Member, user: User) -> None:
    """超管可管全部；理事仅本分会。"""
    if user.role == UserRole.super_admin:
        return
    if user.role == UserRole.council_admin and user.branch_id == member.branch_id:
        return
    raise HTTPException(status_code=403, detail="权限不足 / Forbidden")


@router.post("", status_code=status.HTTP_201_CREATED)
def create_member(
    payload: MemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.super_admin, UserRole.council_admin)
    ),
):
    branch_id = payload.branch_id
    if current_user.role == UserRole.council_admin:
        # 理事只能在本分会建档
        if branch_id and branch_id != current_user.branch_id:
            raise HTTPException(status_code=403, detail="只能管理本分会 / Own branch only")
        branch_id = current_user.branch_id

    user_id = None
    if payload.account_username and payload.account_password:
        exists = (
            db.query(User).filter(User.username == payload.account_username).first()
        )
        if exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已存在 / Username taken",
            )
        account = User(
            username=payload.account_username,
            full_name=payload.chinese_name,
            hashed_password=hash_password(payload.account_password),
            role=UserRole.member,
            is_active=True,
            branch_id=branch_id,
            team_id=payload.team_id,
        )
        db.add(account)
        db.flush()
        user_id = account.id

    data = payload.model_dump(
        exclude={"account_username", "account_password", "branch_id", "join_date"}
    )
    member = Member(
        **data,
        branch_id=branch_id,
        user_id=user_id,
        status=MemberStatus.active,
        join_date=payload.join_date or date.today(),
        last_active_at=datetime.now(timezone.utc),
        created_by=current_user.id,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return _serialize(member, current_user)


@router.get("")
def list_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Member).filter(Member.is_deleted.is_(False))

    role = current_user.role
    if role in {UserRole.super_admin, UserRole.finance, UserRole.event_director}:
        pass
    elif role == UserRole.council_admin and current_user.branch_id:
        query = query.filter(Member.branch_id == current_user.branch_id)
    elif role == UserRole.team_captain:
        team_ids = _own_team_ids(db, current_user) or [-1]
        query = query.filter(Member.team_id.in_(team_ids))
    else:
        # 普通会员仅能看到自己
        query = query.filter(Member.user_id == current_user.id)

    members = query.order_by(Member.id).all()
    return [_serialize(m, current_user) for m in members]


@router.get("/me", response_model=MemberFullOut)
def get_my_member(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = (
        db.query(Member)
        .filter(Member.user_id == current_user.id, Member.is_deleted.is_(False))
        .first()
    )
    if m is None:
        raise HTTPException(status_code=404, detail="尚未建立会员档案 / No member profile")
    return m


@router.put("/me", response_model=MemberFullOut)
def update_my_member(
    payload: MemberSelfUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = (
        db.query(Member)
        .filter(Member.user_id == current_user.id, Member.is_deleted.is_(False))
        .first()
    )
    if m is None:
        raise HTTPException(status_code=404, detail="尚未建立会员档案 / No member profile")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(m, field, value)
    m.updated_by = current_user.id
    m.last_active_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(m)
    return m


@router.get("/{member_id}")
def get_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    m = _get_member(db, member_id)
    return _serialize(m, current_user)


@router.put("/{member_id}")
def update_member(
    member_id: int,
    payload: MemberAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.super_admin, UserRole.council_admin)
    ),
):
    m = _get_member(db, member_id)
    _assert_manage_scope(m, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(m, field, value)
    m.updated_by = current_user.id
    db.commit()
    db.refresh(m)
    return _serialize(m, current_user)


@router.post("/{member_id}/blacklist")
def blacklist_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.super_admin, UserRole.council_admin)
    ),
):
    m = _get_member(db, member_id)
    _assert_manage_scope(m, current_user)
    m.level = MemberLevel.blacklist
    m.updated_by = current_user.id
    db.commit()
    db.refresh(m)
    return _serialize(m, current_user)


@router.post("/{member_id}/promote", response_model=PromoteResult)
def promote_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.super_admin, UserRole.council_admin, UserRole.team_captain
        )
    ),
):
    m = _get_member(db, member_id)

    # 队长仅能操作本队成员
    if current_user.role == UserRole.team_captain:
        if m.team_id not in _own_team_ids(db, current_user):
            raise HTTPException(status_code=403, detail="仅能管理本队 / Own team only")
    elif current_user.role == UserRole.council_admin:
        _assert_manage_scope(m, current_user)

    if m.level != MemberLevel.probationary:
        return PromoteResult(
            id=m.id, level=m.level, promoted=False, reason="非预备会员 / Not probationary"
        )

    # 入会满 3 个月 + 累计出勤≥5 次 + 无欠费
    if not m.join_date or (date.today() - m.join_date) < timedelta(days=_PROMOTE_MIN_DAYS):
        return PromoteResult(
            id=m.id,
            level=m.level,
            promoted=False,
            reason="入会未满3个月 / Membership < 3 months",
        )

    if count_member_checkins(db, m.id) < PROMOTE_MIN_ATTENDANCE:
        return PromoteResult(
            id=m.id,
            level=m.level,
            promoted=False,
            reason=f"出勤未满{PROMOTE_MIN_ATTENDANCE}次 / Attendance < {PROMOTE_MIN_ATTENDANCE}",
        )

    if member_has_outstanding(db, m.id):
        return PromoteResult(
            id=m.id,
            level=m.level,
            promoted=False,
            reason="存在未缴费用 / Outstanding dues",
        )

    m.level = MemberLevel.formal
    m.updated_by = current_user.id
    db.commit()
    return PromoteResult(id=m.id, level=MemberLevel.formal, promoted=True)


@router.post("/sleep-scan")
def sleep_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.super_admin)),
):
    """标记 12 个月未活跃的会员为沉睡（出勤/缴费联动在后续阶段增强）。"""
    threshold = datetime.now(timezone.utc) - timedelta(days=_SLEEP_DAYS)
    candidates = (
        db.query(Member)
        .filter(
            Member.is_deleted.is_(False),
            Member.status == MemberStatus.active,
            Member.last_active_at < threshold,
        )
        .all()
    )
    for m in candidates:
        m.status = MemberStatus.sleeping
        m.updated_by = current_user.id
    db.commit()
    return {"marked_sleeping": len(candidates)}
