from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.activity import (
    Activity,
    ActivityRegistration,
    ActivityStatus,
    RegistrantType,
    RegistrationStatus,
)
from app.models.member import Member, MemberLevel, MemberStatus
from app.models.team import Team
from app.models.user import User, UserRole
from app.schemas.activity import (
    ActivityCreate,
    ActivityOut,
    ActivityRegisterRequest,
    ActivityUpdate,
    AttendanceStats,
    CheckinRequest,
    RegistrationOut,
)
from app.services.notification import notify_activity_registered

router = APIRouter(prefix="/activities", tags=["activity"])

_MANAGE_ROLES = {
    UserRole.super_admin,
    UserRole.council_admin,
    UserRole.team_captain,
    UserRole.event_director,
}
_ACTIVE_REG = (RegistrationStatus.registered, RegistrationStatus.checked_in)


def _get_activity(db: Session, activity_id: int) -> Activity:
    a = (
        db.query(Activity)
        .filter(Activity.id == activity_id, Activity.is_deleted.is_(False))
        .first()
    )
    if a is None:
        raise HTTPException(status_code=404, detail="活动不存在 / Activity not found")
    return a


def _own_team_ids(db: Session, user: User) -> list[int]:
    return [t.id for t in db.query(Team.id).filter(Team.captain_id == user.id).all()]


def _assert_activity_manage(activity: Activity, user: User, db: Session) -> None:
    if user.role == UserRole.super_admin:
        return
    if user.role == UserRole.council_admin and user.branch_id == activity.branch_id:
        return
    if user.role == UserRole.team_captain:
        if activity.team_id and activity.team_id in _own_team_ids(db, user):
            return
    if user.role == UserRole.event_director:
        return
    raise HTTPException(status_code=403, detail="权限不足 / Forbidden")


def _activity_query_for_user(db: Session, user: User):
    q = db.query(Activity).filter(Activity.is_deleted.is_(False))
    if user.role in {UserRole.super_admin, UserRole.finance, UserRole.event_director}:
        return q
    if user.role == UserRole.council_admin and user.branch_id:
        return q.filter(Activity.branch_id == user.branch_id)
    if user.role == UserRole.team_captain:
        team_ids = _own_team_ids(db, user) or [-1]
        return q.filter(
            (Activity.team_id.in_(team_ids)) | (Activity.team_id.is_(None))
        )
    # 普通会员：仅已发布活动（本分会或全协会）
    member = (
        db.query(Member)
        .filter(Member.user_id == user.id, Member.is_deleted.is_(False))
        .first()
    )
    q = q.filter(Activity.status == ActivityStatus.published)
    if member and member.branch_id:
        return q.filter(Activity.branch_id == member.branch_id)
    return q


def _counts(db: Session, activity_id: int) -> dict[str, int]:
    base = db.query(ActivityRegistration).filter(
        ActivityRegistration.activity_id == activity_id,
        ActivityRegistration.is_deleted.is_(False),
        ActivityRegistration.status.in_(_ACTIVE_REG + (RegistrationStatus.absent,)),
    )
    member_reg = base.filter(
        ActivityRegistration.registrant_type == RegistrantType.member
    ).count()
    family_reg = base.filter(
        ActivityRegistration.registrant_type == RegistrantType.family
    ).count()
    checked = base.filter(
        ActivityRegistration.status == RegistrationStatus.checked_in
    ).count()
    return {
        "member_registered_count": member_reg,
        "family_registered_count": family_reg,
        "checked_in_count": checked,
    }


def _to_out(db: Session, activity: Activity) -> ActivityOut:
    data = ActivityOut.model_validate(activity).model_dump()
    data.update(_counts(db, activity.id))
    return ActivityOut(**data)


def _get_member_for_user(db: Session, user: User) -> Member:
    m = (
        db.query(Member)
        .filter(Member.user_id == user.id, Member.is_deleted.is_(False))
        .first()
    )
    if m is None:
        raise HTTPException(
            status_code=404, detail="尚未建立会员档案 / No member profile"
        )
    return m


@router.post("", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(
    payload: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    if current_user.role == UserRole.council_admin:
        if payload.branch_id != current_user.branch_id:
            raise HTTPException(status_code=403, detail="只能管理本分会 / Own branch only")
    if current_user.role == UserRole.team_captain and payload.team_id:
        if payload.team_id not in _own_team_ids(db, current_user):
            raise HTTPException(status_code=403, detail="只能管理本队 / Own team only")

    activity = Activity(**payload.model_dump(), created_by=current_user.id)
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return _to_out(db, activity)


@router.get("", response_model=list[ActivityOut])
def list_activities(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    activities = _activity_query_for_user(db, current_user).order_by(
        Activity.start_at.desc()
    ).all()
    return [_to_out(db, a) for a in activities]


@router.get("/{activity_id}", response_model=ActivityOut)
def get_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    activity = _get_activity(db, activity_id)
    if current_user.role == UserRole.member:
        if activity.status != ActivityStatus.published:
            raise HTTPException(status_code=404, detail="活动不存在 / Activity not found")
    return _to_out(db, activity)


@router.put("/{activity_id}", response_model=ActivityOut)
def update_activity(
    activity_id: int,
    payload: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    activity = _get_activity(db, activity_id)
    _assert_activity_manage(activity, current_user, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(activity, field, value)
    activity.updated_by = current_user.id
    db.commit()
    db.refresh(activity)
    return _to_out(db, activity)


@router.post("/{activity_id}/publish", response_model=ActivityOut)
def publish_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    activity = _get_activity(db, activity_id)
    _assert_activity_manage(activity, current_user, db)
    activity.status = ActivityStatus.published
    activity.updated_by = current_user.id
    db.commit()
    db.refresh(activity)
    return _to_out(db, activity)


@router.post("/{activity_id}/register", response_model=list[RegistrationOut])
def register_activity(
    activity_id: int,
    payload: ActivityRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    activity = _get_activity(db, activity_id)
    if activity.status != ActivityStatus.published:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="活动未开放报名 / Registration closed",
        )
    if activity.course_slots_locked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="球场名额已锁定 / Course slots locked",
        )

    member = _get_member_for_user(db, current_user)
    if member.level == MemberLevel.blacklist:
        raise HTTPException(status_code=403, detail="黑名单会员不可报名 / Blacklisted")
    if member.status != MemberStatus.active:
        raise HTTPException(status_code=403, detail="会员状态不可报名 / Inactive member")

    existing = (
        db.query(ActivityRegistration)
        .filter(
            ActivityRegistration.activity_id == activity_id,
            ActivityRegistration.member_id == member.id,
            ActivityRegistration.registrant_type == RegistrantType.member,
            ActivityRegistration.status.in_(_ACTIVE_REG),
            ActivityRegistration.is_deleted.is_(False),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="已报名 / Already registered",
        )

    member_count = (
        db.query(ActivityRegistration)
        .filter(
            ActivityRegistration.activity_id == activity_id,
            ActivityRegistration.registrant_type == RegistrantType.member,
            ActivityRegistration.status.in_(_ACTIVE_REG),
            ActivityRegistration.is_deleted.is_(False),
        )
        .count()
    )
    if member_count >= activity.max_participants:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="会员名额已满 / Member slots full",
        )

    family_list = payload.family_companions
    if family_list and not activity.family_allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="本活动不允许家属报名 / Family not allowed",
        )
    family_count = (
        db.query(ActivityRegistration)
        .filter(
            ActivityRegistration.activity_id == activity_id,
            ActivityRegistration.registrant_type == RegistrantType.family,
            ActivityRegistration.status.in_(_ACTIVE_REG),
            ActivityRegistration.is_deleted.is_(False),
        )
        .count()
    )
    if family_count + len(family_list) > activity.max_family_slots:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="家属名额已满 / Family slots full",
        )

    rows: list[ActivityRegistration] = []
    member_row = ActivityRegistration(
        activity_id=activity_id,
        member_id=member.id,
        user_id=current_user.id,
        registrant_type=RegistrantType.member,
        status=RegistrationStatus.registered,
        remark=payload.remark,
        created_by=current_user.id,
    )
    db.add(member_row)
    rows.append(member_row)

    for comp in family_list:
        fam = ActivityRegistration(
            activity_id=activity_id,
            member_id=member.id,
            user_id=current_user.id,
            registrant_type=RegistrantType.family,
            family_name=comp.name,
            family_relation=comp.relation,
            status=RegistrationStatus.registered,
            created_by=current_user.id,
        )
        db.add(fam)
        rows.append(fam)

    db.commit()
    for r in rows:
        db.refresh(r)
    notify_activity_registered(
        db,
        activity=activity,
        member=member,
        recipient_user_id=current_user.id,
    )
    db.commit()
    return rows


@router.get("/{activity_id}/registrations", response_model=list[RegistrationOut])
def list_registrations(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    activity = _get_activity(db, activity_id)
    _assert_activity_manage(activity, current_user, db)
    regs = (
        db.query(ActivityRegistration)
        .filter(
            ActivityRegistration.activity_id == activity_id,
            ActivityRegistration.is_deleted.is_(False),
        )
        .order_by(ActivityRegistration.id)
        .all()
    )
    return regs


@router.post("/{activity_id}/checkin", response_model=list[RegistrationOut])
def checkin(
    activity_id: int,
    payload: CheckinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """现场扫码签到：校验 token 后，将该会员在本活动的有效报名行全部签到。"""
    activity = _get_activity(db, activity_id)
    if payload.token != activity.checkin_token:
        raise HTTPException(status_code=403, detail="签到码无效 / Invalid check-in token")
    if activity.status not in {ActivityStatus.published, ActivityStatus.closed}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="活动不可签到 / Check-in not available",
        )

    member = _get_member_for_user(db, current_user)
    regs = (
        db.query(ActivityRegistration)
        .filter(
            ActivityRegistration.activity_id == activity_id,
            ActivityRegistration.member_id == member.id,
            ActivityRegistration.status == RegistrationStatus.registered,
            ActivityRegistration.is_deleted.is_(False),
        )
        .all()
    )
    if not regs:
        raise HTTPException(
            status_code=404, detail="未找到报名记录 / No registration found"
        )

    now = datetime.now(timezone.utc)
    for r in regs:
        r.status = RegistrationStatus.checked_in
        r.checked_in_at = now
        r.updated_by = current_user.id

    member.last_active_at = now
    member.updated_by = current_user.id
    db.commit()
    for r in regs:
        db.refresh(r)
    return regs


@router.post(
    "/{activity_id}/registrations/{reg_id}/mark-absent",
    response_model=RegistrationOut,
)
def mark_absent(
    activity_id: int,
    reg_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    """缺席台账：管理员标记未到场。"""
    activity = _get_activity(db, activity_id)
    _assert_activity_manage(activity, current_user, db)
    reg = (
        db.query(ActivityRegistration)
        .filter(
            ActivityRegistration.id == reg_id,
            ActivityRegistration.activity_id == activity_id,
            ActivityRegistration.is_deleted.is_(False),
        )
        .first()
    )
    if reg is None:
        raise HTTPException(status_code=404, detail="报名不存在 / Not found")
    if reg.status != RegistrationStatus.registered:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前状态不可标记缺席 / Invalid state",
        )
    reg.status = RegistrationStatus.absent
    reg.updated_by = current_user.id
    db.commit()
    db.refresh(reg)
    return reg


@router.get("/{activity_id}/attendance-stats", response_model=AttendanceStats)
def attendance_stats(
    activity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    """出勤率统计（评优依据）。"""
    activity = _get_activity(db, activity_id)
    _assert_activity_manage(activity, current_user, db)

    base = db.query(ActivityRegistration).filter(
        ActivityRegistration.activity_id == activity_id,
        ActivityRegistration.is_deleted.is_(False),
    )
    member_reg = base.filter(
        ActivityRegistration.registrant_type == RegistrantType.member,
        ActivityRegistration.status.in_(
            _ACTIVE_REG + (RegistrationStatus.absent,)
        ),
    ).count()
    family_reg = base.filter(
        ActivityRegistration.registrant_type == RegistrantType.family,
        ActivityRegistration.status.in_(
            _ACTIVE_REG + (RegistrationStatus.absent,)
        ),
    ).count()
    member_checked = base.filter(
        ActivityRegistration.registrant_type == RegistrantType.member,
        ActivityRegistration.status == RegistrationStatus.checked_in,
    ).count()
    family_checked = base.filter(
        ActivityRegistration.registrant_type == RegistrantType.family,
        ActivityRegistration.status == RegistrationStatus.checked_in,
    ).count()
    member_absent = base.filter(
        ActivityRegistration.registrant_type == RegistrantType.member,
        ActivityRegistration.status == RegistrationStatus.absent,
    ).count()

    rate = (member_checked / member_reg * 100) if member_reg else 0.0

    return AttendanceStats(
        activity_id=activity_id,
        member_registered=member_reg,
        family_registered=family_reg,
        member_checked_in=member_checked,
        family_checked_in=family_checked,
        member_absent=member_absent,
        attendance_rate=round(rate, 2),
    )
