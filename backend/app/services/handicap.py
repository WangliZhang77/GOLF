"""差点趋势计算：对比近 12 个月窗口内最早一条记录的起点值与当前值。"""
from datetime import date, timedelta
from decimal import Decimal

from app.models.handicap import HandicapHistory

_TOLERANCE = Decimal("0.1")
_WINDOW_DAYS = 365


def compute_trend(history: list[HandicapHistory], current: Decimal | None) -> str:
    if current is None:
        return "stable"

    cutoff = date.today() - timedelta(days=_WINDOW_DAYS)
    window = [h for h in history if h.date >= cutoff]
    if not window:
        return "stable"

    earliest = min(window, key=lambda h: (h.date, h.id))
    baseline = earliest.old_handicap if earliest.old_handicap is not None else earliest.new_handicap

    diff = current - baseline
    if abs(diff) <= _TOLERANCE:
        return "stable"
    return "declining" if diff < 0 else "rising"
