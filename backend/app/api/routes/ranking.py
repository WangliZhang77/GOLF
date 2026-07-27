from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.competition import Competition, CompetitionStatus
from app.models.grouping import CompetitionGroupPlayer
from app.models.ranking import Ranking, RankingScope
from app.models.scorecard import ScoreCard, ScoreCardStatus
from app.models.user import User, UserRole
from app.schemas.ranking import RankingAwardUpdate, RankingOut, RankingPreviewItem
from app.services.ranking import compute_individual_rankings, compute_team_rankings

router = APIRouter(prefix="/competitions", tags=["ranking"])

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


def _approved_cards(db: Session, competition_id: int) -> list[ScoreCard]:
    return (
        db.query(ScoreCard)
        .filter(
            ScoreCard.competition_id == competition_id,
            ScoreCard.status == ScoreCardStatus.approved,
            ScoreCard.is_deleted.is_(False),
        )
        .all()
    )


def _cards_with_team(db: Session, competition_id: int, cards: list[ScoreCard]) -> list[tuple[ScoreCard, int]]:
    member_ids = [c.member_id for c in cards]
    if not member_ids:
        return []
    team_by_member = {
        row.member_id: row.team_id
        for row in db.query(CompetitionGroupPlayer)
        .filter(
            CompetitionGroupPlayer.competition_id == competition_id,
            CompetitionGroupPlayer.member_id.in_(member_ids),
            CompetitionGroupPlayer.is_deleted.is_(False),
        )
        .all()
    }
    return [
        (card, team_by_member[card.member_id])
        for card in cards
        if team_by_member.get(card.member_id) is not None
    ]


def _assert_all_approved(db: Session, competition_id: int) -> None:
    total = (
        db.query(ScoreCard)
        .filter(ScoreCard.competition_id == competition_id, ScoreCard.is_deleted.is_(False))
        .count()
    )
    approved = len(_approved_cards(db, competition_id))
    if total == 0 or approved != total:
        pending = total - approved
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"仍有{pending}张计分卡未通过审核 / {pending} scorecards not yet approved",
        )


@router.get("/{competition_id}/rankings/preview", response_model=list[RankingPreviewItem])
def preview_rankings(
    competition_id: int,
    scope: RankingScope | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user)

    cards = _approved_cards(db, competition_id)
    result: list[RankingPreviewItem] = []
    if scope is None or scope == RankingScope.individual:
        result += [
            RankingPreviewItem(**row.__dict__) for row in compute_individual_rankings(cards)
        ]
    if scope is None or scope == RankingScope.team:
        result += [
            RankingPreviewItem(**row.__dict__)
            for row in compute_team_rankings(_cards_with_team(db, competition_id, cards))
        ]
    return result


@router.post("/{competition_id}/rankings/publish", response_model=list[RankingOut])
def publish_rankings(
    competition_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user)

    if competition.status not in (CompetitionStatus.review, CompetitionStatus.completed):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="当前状态不可发布排名 / Cannot publish ranking from current status",
        )
    _assert_all_approved(db, competition_id)

    now = datetime.now(timezone.utc)
    old_rows = (
        db.query(Ranking)
        .filter(Ranking.competition_id == competition_id, Ranking.is_deleted.is_(False))
        .all()
    )
    for row in old_rows:
        row.is_deleted = True
        row.deleted_at = now
        row.deleted_by = current_user.id

    cards = _approved_cards(db, competition_id)
    computed = compute_individual_rankings(cards) + compute_team_rankings(
        _cards_with_team(db, competition_id, cards)
    )
    new_rows = [
        Ranking(
            competition_id=competition_id,
            scope=r.scope,
            member_id=r.member_id,
            team_id=r.team_id,
            rank=r.rank,
            score=r.score,
            award=r.award,
            created_by=current_user.id,
        )
        for r in computed
    ]
    db.add_all(new_rows)

    competition.status = CompetitionStatus.completed
    competition.updated_by = current_user.id
    db.commit()
    for row in new_rows:
        db.refresh(row)
    return new_rows


@router.get("/{competition_id}/rankings", response_model=list[RankingOut])
def list_rankings(
    competition_id: int,
    scope: RankingScope | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_competition(db, competition_id)
    q = db.query(Ranking).filter(
        Ranking.competition_id == competition_id, Ranking.is_deleted.is_(False)
    )
    if scope is not None:
        q = q.filter(Ranking.scope == scope)
    return q.order_by(Ranking.scope, Ranking.rank).all()


@router.patch("/{competition_id}/rankings/{ranking_id}", response_model=RankingOut)
def update_ranking_award(
    competition_id: int,
    ranking_id: int,
    payload: RankingAwardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    competition = _get_competition(db, competition_id)
    _assert_competition_manage(competition, current_user)
    row = (
        db.query(Ranking)
        .filter(
            Ranking.id == ranking_id,
            Ranking.competition_id == competition_id,
            Ranking.is_deleted.is_(False),
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="排名不存在 / Ranking not found")
    row.award = payload.award
    row.updated_by = current_user.id
    db.commit()
    db.refresh(row)
    return row
