from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.competition import Competition, CompetitionStatus
from app.models.grouping import CompetitionGroupPlayer
from app.models.member import Member
from app.models.scorecard import ScoreCard, ScoreCardStatus, ScoreReview, ScoreReviewStatus
from app.models.user import User, UserRole
from app.schemas.scoring import (
    AdminReviewRequest,
    HoleUpdateRequest,
    PeerConfirmRequest,
    ScoreCardOut,
    ScoreReviewOut,
)
from app.services.scoring import is_complete, recompute_scores

router = APIRouter(prefix="/competitions", tags=["scoring"])

_MANAGE_ROLES = {
    UserRole.super_admin,
    UserRole.council_admin,
    UserRole.event_director,
}
_EDITABLE_STATUSES = (ScoreCardStatus.draft, ScoreCardStatus.rejected)


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


def _get_scorecard(db: Session, competition_id: int, card_id: int) -> ScoreCard:
    card = (
        db.query(ScoreCard)
        .filter(
            ScoreCard.id == card_id,
            ScoreCard.competition_id == competition_id,
            ScoreCard.is_deleted.is_(False),
        )
        .first()
    )
    if card is None:
        raise HTTPException(status_code=404, detail="计分卡不存在 / Scorecard not found")
    return card


def _member_group_id(db: Session, competition_id: int, member_id: int) -> int | None:
    row = (
        db.query(CompetitionGroupPlayer)
        .filter(
            CompetitionGroupPlayer.competition_id == competition_id,
            CompetitionGroupPlayer.member_id == member_id,
            CompetitionGroupPlayer.is_deleted.is_(False),
        )
        .first()
    )
    return row.group_id if row else None


def _assert_can_view_card(card: ScoreCard, user: User, db: Session) -> None:
    if user.role in _MANAGE_ROLES:
        return
    member = _get_member_for_user(db, user)
    if card.member_id == member.id:
        return
    my_group = _member_group_id(db, card.competition_id, member.id)
    if my_group is not None and my_group == card.group_id:
        return
    raise HTTPException(status_code=403, detail="权限不足 / Forbidden")


@router.patch("/{competition_id}/scorecards/{card_id}/hole", response_model=ScoreCardOut)
def update_hole(
    competition_id: int,
    card_id: int,
    payload: HoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    competition = _get_competition(db, competition_id)
    card = _get_scorecard(db, competition_id, card_id)

    is_manager = current_user.role in _MANAGE_ROLES
    if not is_manager:
        member = _get_member_for_user(db, current_user)
        if card.member_id != member.id:
            raise HTTPException(status_code=403, detail="仅本人可填写 / Owner only")
        if card.status not in _EDITABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="已提交，不可修改 / Already submitted, cannot edit",
            )
        if competition.status != CompetitionStatus.playing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="比赛未开始，不可记分 / Competition is not in play",
            )
    else:
        _assert_competition_manage(competition, current_user)

    setattr(card, f"hole{payload.hole_number}", payload.strokes)
    recompute_scores(card)
    card.updated_by = current_user.id
    db.commit()
    db.refresh(card)
    return card


@router.post("/{competition_id}/scorecards/{card_id}/submit", response_model=ScoreCardOut)
def submit_scorecard(
    competition_id: int,
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    card = _get_scorecard(db, competition_id, card_id)
    member = _get_member_for_user(db, current_user)
    if card.member_id != member.id:
        raise HTTPException(status_code=403, detail="仅本人可提交 / Owner only")
    if card.status not in _EDITABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="当前状态不可提交 / Invalid state"
        )
    if not is_complete(card):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="请先填写完整18洞成绩 / All 18 holes must be filled before submitting",
        )
    card.status = ScoreCardStatus.submitted
    card.updated_by = current_user.id
    db.commit()
    db.refresh(card)
    return card


@router.post(
    "/{competition_id}/scorecards/{card_id}/peer-confirm", response_model=ScoreCardOut
)
def peer_confirm(
    competition_id: int,
    card_id: int,
    payload: PeerConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    card = _get_scorecard(db, competition_id, card_id)
    member = _get_member_for_user(db, current_user)
    if card.member_id == member.id:
        raise HTTPException(status_code=403, detail="不能确认自己的成绩 / Cannot confirm your own card")
    my_group = _member_group_id(db, competition_id, member.id)
    if my_group is None or my_group != card.group_id:
        raise HTTPException(status_code=403, detail="仅同组球员可确认 / Group members only")
    if card.status != ScoreCardStatus.submitted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="当前状态不可确认 / Invalid state"
        )

    db.add(
        ScoreReview(
            score_id=card.id,
            reviewer_id=current_user.id,
            status=ScoreReviewStatus.checking,
            comment=payload.comment,
            created_by=current_user.id,
        )
    )
    card.status = ScoreCardStatus.checking
    card.updated_by = current_user.id
    db.commit()
    db.refresh(card)
    return card


@router.post(
    "/{competition_id}/scorecards/{card_id}/admin-review", response_model=ScoreCardOut
)
def admin_review(
    competition_id: int,
    card_id: int,
    payload: AdminReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user)
    card = _get_scorecard(db, competition_id, card_id)
    if card.status not in (ScoreCardStatus.submitted, ScoreCardStatus.checking):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="当前状态不可审核 / Invalid state"
        )

    new_status = (
        ScoreReviewStatus.approved if payload.approve else ScoreReviewStatus.rejected
    )
    db.add(
        ScoreReview(
            score_id=card.id,
            reviewer_id=current_user.id,
            status=new_status,
            comment=payload.comment,
            created_by=current_user.id,
        )
    )
    card.status = (
        ScoreCardStatus.approved if payload.approve else ScoreCardStatus.rejected
    )
    card.updated_by = current_user.id
    db.commit()
    db.refresh(card)
    return card


@router.get("/{competition_id}/scorecards/mine", response_model=ScoreCardOut)
def my_scorecard(
    competition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    member = _get_member_for_user(db, current_user)
    card = (
        db.query(ScoreCard)
        .filter(
            ScoreCard.competition_id == competition_id,
            ScoreCard.member_id == member.id,
            ScoreCard.is_deleted.is_(False),
        )
        .first()
    )
    if card is None:
        raise HTTPException(status_code=404, detail="计分卡不存在 / Scorecard not found")
    return card


@router.get("/{competition_id}/scorecards", response_model=list[ScoreCardOut])
def list_scorecards(
    competition_id: int,
    group_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_competition(db, competition_id)
    q = db.query(ScoreCard).filter(
        ScoreCard.competition_id == competition_id,
        ScoreCard.is_deleted.is_(False),
    )
    if current_user.role in _MANAGE_ROLES:
        if group_id is not None:
            q = q.filter(ScoreCard.group_id == group_id)
    else:
        member = _get_member_for_user(db, current_user)
        my_group = _member_group_id(db, competition_id, member.id)
        if my_group is None:
            return []
        q = q.filter(ScoreCard.group_id == my_group)
    return q.order_by(ScoreCard.id).all()


@router.get("/{competition_id}/scorecards/{card_id}", response_model=ScoreCardOut)
def get_scorecard(
    competition_id: int,
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_competition(db, competition_id)
    card = _get_scorecard(db, competition_id, card_id)
    _assert_can_view_card(card, current_user, db)
    return card


@router.get(
    "/{competition_id}/scorecards/{card_id}/reviews", response_model=list[ScoreReviewOut]
)
def list_score_reviews(
    competition_id: int,
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_competition(db, competition_id)
    card = _get_scorecard(db, competition_id, card_id)
    if current_user.role not in _MANAGE_ROLES:
        member = _get_member_for_user(db, current_user)
        if card.member_id != member.id:
            raise HTTPException(status_code=403, detail="权限不足 / Forbidden")
    return (
        db.query(ScoreReview)
        .filter(ScoreReview.score_id == card.id, ScoreReview.is_deleted.is_(False))
        .order_by(ScoreReview.id)
        .all()
    )


@router.post("/{competition_id}/close-play")
def close_play(
    competition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user)

    if competition.status != CompetitionStatus.playing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前状态不可结束比赛 / Cannot close play from current status",
        )

    draft_count = (
        db.query(ScoreCard)
        .filter(
            ScoreCard.competition_id == competition_id,
            ScoreCard.status == ScoreCardStatus.draft,
            ScoreCard.is_deleted.is_(False),
        )
        .count()
    )
    if draft_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"仍有{draft_count}张计分卡未提交 / {draft_count} scorecards not yet submitted",
        )

    competition.status = CompetitionStatus.review
    competition.updated_by = current_user.id
    db.commit()
    return {"id": competition.id, "status": competition.status.value}
