from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.ranking import RankingScope


class RankingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competition_id: int
    scope: RankingScope
    member_id: int | None
    team_id: int | None
    rank: int
    score: Decimal
    award: str | None


class RankingPreviewItem(BaseModel):
    scope: RankingScope
    member_id: int | None
    team_id: int | None
    rank: int
    score: Decimal
    award: str | None


class RankingAwardUpdate(BaseModel):
    award: str | None = None
