"""18洞计分：出杆/总杆/净杆的纯计算逻辑，供 hole 录入路由复用。"""
from decimal import Decimal

from app.models.scorecard import ScoreCard

HOLE_NUMBERS = list(range(1, 19))
FRONT_NINE = list(range(1, 10))
BACK_NINE = list(range(10, 19))


def _hole_value(card: ScoreCard, hole_number: int) -> int | None:
    return getattr(card, f"hole{hole_number}")


def is_complete(card: ScoreCard) -> bool:
    return all(_hole_value(card, n) is not None for n in HOLE_NUMBERS)


def recompute_scores(card: ScoreCard) -> None:
    """未填的洞按 0 计入，仅用于练习中的实时小计展示；提交前必须 18 洞全部填写。"""
    out_score = sum(_hole_value(card, n) or 0 for n in FRONT_NINE)
    in_score = sum(_hole_value(card, n) or 0 for n in BACK_NINE)
    total = out_score + in_score

    card.out_score = out_score
    card.in_score = in_score
    card.total_score = total

    if card.handicap_snapshot is not None:
        card.net_score = Decimal(total) - card.handicap_snapshot
    else:
        card.net_score = None
