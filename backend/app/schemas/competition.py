from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.competition import (
    CompetitionRegApprovalStatus,
    CompetitionRegPaymentStatus,
    CompetitionStatus,
    CompetitionType,
)


class CompetitionBase(BaseModel):
    name: str
    description: str | None = None
    competition_type: CompetitionType
    level: str | None = None
    course_id: int | None = None
    branch_id: int | None = None
    start_time: datetime
    end_time: datetime | None = None
    registration_deadline: datetime | None = None
    fee: Decimal | None = None
    max_players: int = Field(default=40, ge=1)
    max_handicap: Decimal | None = None


class CompetitionCreate(CompetitionBase):
    pass


class CompetitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    competition_type: CompetitionType | None = None
    level: str | None = None
    course_id: int | None = None
    branch_id: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    registration_deadline: datetime | None = None
    fee: Decimal | None = None
    max_players: int | None = Field(default=None, ge=1)
    max_handicap: Decimal | None = None
    status: CompetitionStatus | None = None


class CompetitionOut(CompetitionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: CompetitionStatus
    registered_count: int | None = None
    approved_count: int | None = None
    # 仅当调用方是普通会员时由列表接口注入：本人报名状态（未报名则为 None）
    my_registration_status: CompetitionRegApprovalStatus | None = None


class CompetitionRegisterRequest(BaseModel):
    remark: str | None = None


class CompetitionRegistrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    competition_id: int
    member_id: int
    user_id: int
    team_id: int | None
    registration_time: datetime
    payment_status: CompetitionRegPaymentStatus
    approval_status: CompetitionRegApprovalStatus
    remark: str | None


class CompetitionApprovalRequest(BaseModel):
    approve: bool
    remark: str | None = None
