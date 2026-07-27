from decimal import Decimal

from pydantic import BaseModel


class MemberAnalytics(BaseModel):
    total: int
    new_last_30d: int
    active: int
    sleeping: int
    team_count: int


class ActivityTrendPoint(BaseModel):
    month: str
    active_member_count: int


class MostAttendedActivity(BaseModel):
    id: int
    title: str
    count: int


class ActivityAnalytics(BaseModel):
    total: int
    avg_participants: float
    most_attended: MostAttendedActivity | None
    active_trend: list[ActivityTrendPoint]


class CompetitionAnalytics(BaseModel):
    total: int
    total_participants: int
    avg_net_score: float | None
    handicap_change: float | None


class FinanceAnalytics(BaseModel):
    income: Decimal
    expense: Decimal
    profit: Decimal
    sponsorship_total: Decimal


class AnalyticsDashboardOut(BaseModel):
    members: MemberAnalytics
    activities: ActivityAnalytics
    competitions: CompetitionAnalytics
    finance: FinanceAnalytics
