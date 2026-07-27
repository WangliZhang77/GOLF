from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.competition import (
    Competition,
    CompetitionRegApprovalStatus,
    CompetitionRegistration,
    CompetitionStatus,
)
from app.models.grouping import CompetitionGroup, CompetitionGroupPlayer, GroupStatus
from app.models.member import Member
from app.models.scorecard import ScoreCard, ScoreCardStatus
from app.models.user import User, UserRole
from app.schemas.grouping import (
    CompetitionGroupOut,
    GenerateGroupsRequest,
    GroupUpdate,
    MovePlayerRequest,
    SwapPlayersRequest,
)
from app.services.grouping import GroupingPlayer, generate_groups

router = APIRouter(prefix="/competitions", tags=["grouping"])

_MANAGE_ROLES = {
    UserRole.super_admin,
    UserRole.council_admin,
    UserRole.event_director,
}


def _get_competition(db: Session, competition_id: int) -> Competition:
    c = (
        db.query(Competition)
        .filter(Competition.id == competition_id, Competition.is_deleted.is_(False))
        .first()
    )
    if c is None:
        raise HTTPException(status_code=404, detail="赛事不存在 / Competition not found")
    return c


def _assert_competition_manage(competition: Competition, user: User) -> None:
    if user.role in {UserRole.super_admin, UserRole.event_director}:
        return
    if (
        user.role == UserRole.council_admin
        and competition.branch_id is not None
        and user.branch_id == competition.branch_id
    ):
        return
    raise HTTPException(status_code=403, detail="权限不足 / Forbidden")


def _get_member_for_user(db: Session, user: User) -> Member:
    m = (
        db.query(Member)
        .filter(Member.user_id == user.id, Member.is_deleted.is_(False))
        .first()
    )
    if m is None:
        raise HTTPException(status_code=404, detail="尚未建立会员档案 / No member profile")
    return m


def _get_group(db: Session, competition_id: int, group_id: int) -> CompetitionGroup:
    g = (
        db.query(CompetitionGroup)
        .filter(
            CompetitionGroup.id == group_id,
            CompetitionGroup.competition_id == competition_id,
            CompetitionGroup.is_deleted.is_(False),
        )
        .first()
    )
    if g is None:
        raise HTTPException(status_code=404, detail="分组不存在 / Group not found")
    return g


def _to_group_out(db: Session, group: CompetitionGroup) -> CompetitionGroupOut:
    players = (
        db.query(CompetitionGroupPlayer)
        .filter(
            CompetitionGroupPlayer.group_id == group.id,
            CompetitionGroupPlayer.is_deleted.is_(False),
        )
        .order_by(CompetitionGroupPlayer.order_number)
        .all()
    )
    data = CompetitionGroupOut.model_validate(group).model_dump()
    data["players"] = players
    return CompetitionGroupOut(**data)


@router.post("/{competition_id}/groups/generate", response_model=list[CompetitionGroupOut])
def generate_competition_groups(
    competition_id: int,
    payload: GenerateGroupsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user)

    if competition.status not in (CompetitionStatus.open, CompetitionStatus.closed):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="仅可在开放/结束报名阶段分组 / Grouping only allowed before play starts",
        )

    existing = (
        db.query(CompetitionGroup)
        .filter(
            CompetitionGroup.competition_id == competition_id,
            CompetitionGroup.is_deleted.is_(False),
        )
        .count()
    )
    if existing and not payload.force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="已存在分组，如需重新生成请传 force=true / Groups already exist, pass force=true to regenerate",
        )
    if existing and payload.force:
        now = datetime.now(timezone.utc)
        old_groups = (
            db.query(CompetitionGroup)
            .filter(
                CompetitionGroup.competition_id == competition_id,
                CompetitionGroup.is_deleted.is_(False),
            )
            .all()
        )
        for g in old_groups:
            g.is_deleted = True
            g.deleted_at = now
            g.deleted_by = current_user.id
        old_players = (
            db.query(CompetitionGroupPlayer)
            .filter(
                CompetitionGroupPlayer.competition_id == competition_id,
                CompetitionGroupPlayer.is_deleted.is_(False),
            )
            .all()
        )
        for p in old_players:
            p.is_deleted = True
            p.deleted_at = now
            p.deleted_by = current_user.id
        db.flush()

    regs = (
        db.query(CompetitionRegistration, Member)
        .join(Member, Member.id == CompetitionRegistration.member_id)
        .filter(
            CompetitionRegistration.competition_id == competition_id,
            CompetitionRegistration.approval_status == CompetitionRegApprovalStatus.approved,
            CompetitionRegistration.is_deleted.is_(False),
        )
        .all()
    )
    players = [
        GroupingPlayer(
            member_id=reg.member_id,
            handicap=member.handicap,
            team_id=reg.team_id,
            registration_id=reg.id,
        )
        for reg, member in regs
    ]

    grouped = generate_groups(players, group_size=payload.group_size)

    result_groups: list[CompetitionGroup] = []
    for gi, group_players in enumerate(grouped):
        tee_time = (
            payload.first_tee_time + timedelta(minutes=gi * payload.interval_minutes)
            if payload.first_tee_time
            else None
        )
        group = CompetitionGroup(
            competition_id=competition_id,
            group_number=gi + 1,
            tee_time=tee_time,
            starting_hole=payload.starting_hole,
            status=GroupStatus.scheduled,
            created_by=current_user.id,
        )
        db.add(group)
        db.flush()
        for oi, gp in enumerate(group_players):
            db.add(
                CompetitionGroupPlayer(
                    competition_id=competition_id,
                    group_id=group.id,
                    member_id=gp.member_id,
                    registration_id=gp.registration_id,
                    order_number=oi + 1,
                    handicap=gp.handicap,
                    team_id=gp.team_id,
                    created_by=current_user.id,
                )
            )
        result_groups.append(group)

    db.commit()
    for g in result_groups:
        db.refresh(g)
    return [_to_group_out(db, g) for g in result_groups]


@router.get("/{competition_id}/groups", response_model=list[CompetitionGroupOut])
def list_competition_groups(
    competition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_competition(db, competition_id)
    groups = (
        db.query(CompetitionGroup)
        .filter(
            CompetitionGroup.competition_id == competition_id,
            CompetitionGroup.is_deleted.is_(False),
        )
        .order_by(CompetitionGroup.group_number)
        .all()
    )
    return [_to_group_out(db, g) for g in groups]


@router.get("/{competition_id}/groups/my-group", response_model=CompetitionGroupOut)
def my_group(
    competition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_competition(db, competition_id)
    member = _get_member_for_user(db, current_user)
    player = (
        db.query(CompetitionGroupPlayer)
        .filter(
            CompetitionGroupPlayer.competition_id == competition_id,
            CompetitionGroupPlayer.member_id == member.id,
            CompetitionGroupPlayer.is_deleted.is_(False),
        )
        .first()
    )
    if player is None:
        raise HTTPException(status_code=404, detail="尚未分组 / Not grouped yet")
    group = _get_group(db, competition_id, player.group_id)
    return _to_group_out(db, group)


@router.get("/{competition_id}/groups/{group_id}", response_model=CompetitionGroupOut)
def get_competition_group(
    competition_id: int,
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_competition(db, competition_id)
    group = _get_group(db, competition_id, group_id)
    return _to_group_out(db, group)


@router.put("/{competition_id}/groups/{group_id}", response_model=CompetitionGroupOut)
def update_competition_group(
    competition_id: int,
    group_id: int,
    payload: GroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user)
    group = _get_group(db, competition_id, group_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    group.updated_by = current_user.id
    db.commit()
    db.refresh(group)
    return _to_group_out(db, group)


@router.post(
    "/{competition_id}/groups/players/{player_id}/move",
    response_model=CompetitionGroupOut,
)
def move_player(
    competition_id: int,
    player_id: int,
    payload: MovePlayerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user)
    player = (
        db.query(CompetitionGroupPlayer)
        .filter(
            CompetitionGroupPlayer.id == player_id,
            CompetitionGroupPlayer.competition_id == competition_id,
            CompetitionGroupPlayer.is_deleted.is_(False),
        )
        .first()
    )
    if player is None:
        raise HTTPException(status_code=404, detail="分组球员不存在 / Player not found")
    target_group = _get_group(db, competition_id, payload.target_group_id)

    if payload.order_number is not None:
        order_number = payload.order_number
    else:
        max_order = (
            db.query(CompetitionGroupPlayer)
            .filter(
                CompetitionGroupPlayer.group_id == target_group.id,
                CompetitionGroupPlayer.is_deleted.is_(False),
            )
            .count()
        )
        order_number = max_order + 1

    player.group_id = target_group.id
    player.order_number = order_number
    player.updated_by = current_user.id
    db.commit()
    db.refresh(target_group)
    return _to_group_out(db, target_group)


@router.post("/{competition_id}/groups/swap", response_model=list[CompetitionGroupOut])
def swap_players(
    competition_id: int,
    payload: SwapPlayersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user)

    def _get_player(pid: int) -> CompetitionGroupPlayer:
        p = (
            db.query(CompetitionGroupPlayer)
            .filter(
                CompetitionGroupPlayer.id == pid,
                CompetitionGroupPlayer.competition_id == competition_id,
                CompetitionGroupPlayer.is_deleted.is_(False),
            )
            .first()
        )
        if p is None:
            raise HTTPException(status_code=404, detail="分组球员不存在 / Player not found")
        return p

    a = _get_player(payload.player_id_a)
    b = _get_player(payload.player_id_b)

    a.group_id, b.group_id = b.group_id, a.group_id
    a.order_number, b.order_number = b.order_number, a.order_number
    a.updated_by = current_user.id
    b.updated_by = current_user.id
    db.commit()

    group_a = _get_group(db, competition_id, a.group_id)
    group_b = _get_group(db, competition_id, b.group_id)
    return [_to_group_out(db, group_a), _to_group_out(db, group_b)]


@router.post("/{competition_id}/start")
def start_competition(
    competition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user)

    if competition.status not in (CompetitionStatus.open, CompetitionStatus.closed):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前状态不可开始比赛 / Cannot start from current status",
        )

    group_count = (
        db.query(CompetitionGroup)
        .filter(
            CompetitionGroup.competition_id == competition_id,
            CompetitionGroup.is_deleted.is_(False),
        )
        .count()
    )
    if group_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="尚未分组 / No groups generated yet"
        )

    approved_member_ids = {
        mid
        for (mid,) in db.query(CompetitionRegistration.member_id)
        .filter(
            CompetitionRegistration.competition_id == competition_id,
            CompetitionRegistration.approval_status == CompetitionRegApprovalStatus.approved,
            CompetitionRegistration.is_deleted.is_(False),
        )
        .all()
    }
    grouped_member_ids = {
        mid
        for (mid,) in db.query(CompetitionGroupPlayer.member_id)
        .filter(
            CompetitionGroupPlayer.competition_id == competition_id,
            CompetitionGroupPlayer.is_deleted.is_(False),
        )
        .all()
    }
    unassigned = sorted(approved_member_ids - grouped_member_ids)
    if unassigned:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"仍有会员未分组 / Members not yet grouped: {unassigned}",
        )

    # 开始比赛：为每个已分组会员建一张草稿计分卡，差点按分组时刻快照
    grouped_players = (
        db.query(CompetitionGroupPlayer)
        .filter(
            CompetitionGroupPlayer.competition_id == competition_id,
            CompetitionGroupPlayer.is_deleted.is_(False),
        )
        .all()
    )
    for gp in grouped_players:
        existing_card = (
            db.query(ScoreCard)
            .filter(
                ScoreCard.competition_id == competition_id,
                ScoreCard.member_id == gp.member_id,
                ScoreCard.is_deleted.is_(False),
            )
            .first()
        )
        if existing_card:
            continue
        db.add(
            ScoreCard(
                competition_id=competition_id,
                member_id=gp.member_id,
                group_id=gp.group_id,
                handicap_snapshot=gp.handicap,
                status=ScoreCardStatus.draft,
                created_by=current_user.id,
            )
        )

    competition.status = CompetitionStatus.playing
    competition.updated_by = current_user.id
    db.commit()
    return {"id": competition.id, "status": competition.status.value}
