from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.handicap import HandicapSource


class HandicapAdjustRequest(BaseModel):
    new_handicap: Decimal
    remark: str | None = None


class HandicapHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: int
    date: date
    old_handicap: Decimal | None
    new_handicap: Decimal
    source: HandicapSource
    competition_id: int | None
    remark: str | None


class HandicapDashboardOut(BaseModel):
    member_id: int
    current_handicap: Decimal | None
    trend: str  # declining / rising / stable
    history: list[HandicapHistoryOut]
