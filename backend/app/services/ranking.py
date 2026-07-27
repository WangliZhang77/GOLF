"""排名计算：纯函数，供 preview/publish 复用。个人按净杆升序；球队按队内净杆均值升序（不同人数不吃亏）。"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.models.ranking import RankingScope
from app.models.scorecard import ScoreCard

AWARD_LABELS = ["champion", "runner_up", "third"]


@dataclass
class RankingRow:
    scope: RankingScope
    member_id: int | None
    team_id: int | None
    rank: int
    score: Decimal
    award: str | None


def _award_for(index: int) -> str | None:
    return AWARD_LABELS[index] if index < len(AWARD_LABELS) else None


def compute_individual_rankings(cards: list[ScoreCard]) -> list[RankingRow]:
    ordered = sorted(cards, key=lambda c: (c.net_score, c.member_id))
    return [
        RankingRow(
            scope=RankingScope.individual,
            member_id=card.member_id,
            team_id=None,
            rank=i + 1,
            score=card.net_score,
            award=_award_for(i),
        )
        for i, card in enumerate(ordered)
    ]


def compute_team_rankings(cards_with_team: list[tuple[ScoreCard, int]]) -> list[RankingRow]:
    grouped: dict[int, list[Decimal]] = {}
    for card, team_id in cards_with_team:
        grouped.setdefault(team_id, []).append(card.net_score)

    averages: list[tuple[int, Decimal]] = []
    for team_id, scores in grouped.items():
        avg = (sum(scores) / len(scores)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        averages.append((team_id, avg))
    averages.sort(key=lambda x: (x[1], x[0]))

    return [
        RankingRow(
            scope=RankingScope.team,
            member_id=None,
            team_id=team_id,
            rank=i + 1,
            score=avg,
            award=_award_for(i),
        )
        for i, (team_id, avg) in enumerate(averages)
    ]
