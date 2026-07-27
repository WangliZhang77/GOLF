from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.scorecard import ScoreCardStatus, ScoreReviewStatus


class ScoreCardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competition_id: int
    member_id: int
    group_id: int
    hole1: int | None
    hole2: int | None
    hole3: int | None
    hole4: int | None
    hole5: int | None
    hole6: int | None
    hole7: int | None
    hole8: int | None
    hole9: int | None
    hole10: int | None
    hole11: int | None
    hole12: int | None
    hole13: int | None
    hole14: int | None
    hole15: int | None
    hole16: int | None
    hole17: int | None
    hole18: int | None
    out_score: int | None
    in_score: int | None
    total_score: int | None
    handicap_snapshot: Decimal | None
    net_score: Decimal | None
    status: ScoreCardStatus


class HoleUpdateRequest(BaseModel):
    hole_number: int = Field(ge=1, le=18)
    strokes: int = Field(ge=1, le=20)


class PeerConfirmRequest(BaseModel):
    comment: str | None = None


class AdminReviewRequest(BaseModel):
    approve: bool
    comment: str | None = None


class ScoreReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    score_id: int
    reviewer_id: int
    status: ScoreReviewStatus
    comment: str | None
