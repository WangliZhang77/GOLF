from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.grouping import GroupStatus


class GenerateGroupsRequest(BaseModel):
    group_size: int = Field(default=4, ge=2)
    force: bool = False
    first_tee_time: datetime | None = None
    interval_minutes: int = Field(default=10, ge=1)
    starting_hole: int = Field(default=1, ge=1, le=18)


class CompetitionGroupPlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    member_id: int
    registration_id: int | None
    order_number: int
    handicap: Decimal | None
    team_id: int | None


class CompetitionGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competition_id: int
    group_number: int
    tee_time: datetime | None
    starting_hole: int
    status: GroupStatus
    players: list[CompetitionGroupPlayerOut] = Field(default_factory=list)


class GroupUpdate(BaseModel):
    tee_time: datetime | None = None
    starting_hole: int | None = Field(default=None, ge=1, le=18)
    status: GroupStatus | None = None


class MovePlayerRequest(BaseModel):
    target_group_id: int
    order_number: int | None = None


class SwapPlayersRequest(BaseModel):
    player_id_a: int
    player_id_b: int
