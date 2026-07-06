from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.activity import (
    ActivityStatus,
    ActivityType,
    RegistrantType,
    RegistrationStatus,
)


class ActivityBase(BaseModel):
    title: str
    description: str | None = None
    activity_type: ActivityType
    branch_id: int
    team_id: int | None = None
    location: str | None = None
    course_name: str | None = None
    start_at: datetime
    end_at: datetime | None = None
    max_participants: int = Field(default=20, ge=1)
    max_family_slots: int = Field(default=0, ge=0)
    family_allowed: bool = False
    course_slots_locked: bool = False
    simple_scoring_enabled: bool = False


class ActivityCreate(ActivityBase):
    pass


class ActivityUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    activity_type: ActivityType | None = None
    location: str | None = None
    course_name: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    max_participants: int | None = Field(default=None, ge=1)
    max_family_slots: int | None = Field(default=None, ge=0)
    family_allowed: bool | None = None
    course_slots_locked: bool | None = None
    simple_scoring_enabled: bool | None = None
    status: ActivityStatus | None = None


class ActivityOut(ActivityBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ActivityStatus
    checkin_token: str
    member_registered_count: int | None = None
    family_registered_count: int | None = None
    checked_in_count: int | None = None


class FamilyCompanion(BaseModel):
    name: str
    relation: str | None = None


class ActivityRegisterRequest(BaseModel):
    """会员报名：本人 + 可选随行家属（分行入库）。"""

    family_companions: list[FamilyCompanion] = Field(default_factory=list)
    remark: str | None = None


class RegistrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_id: int
    member_id: int
    user_id: int
    registrant_type: RegistrantType
    family_name: str | None
    family_relation: str | None
    status: RegistrationStatus
    checked_in_at: datetime | None
    total_strokes: int | None
    remark: str | None


class CheckinRequest(BaseModel):
    """扫码签到：携带活动 checkin_token。"""

    token: str


class AttendanceStats(BaseModel):
    activity_id: int
    member_registered: int
    family_registered: int
    member_checked_in: int
    family_checked_in: int
    member_absent: int
    attendance_rate: float  # 会员签到率 = checked_in / registered
