from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.notification import MessageType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_type: MessageType
    title_zh: str
    title_en: str
    body_zh: str
    body_en: str
    is_read: bool
    read_at: datetime | None
    related_member_id: int | None
    related_activity_id: int | None
    related_ledger_id: int | None
    sent_by: int | None
    created_at: datetime


class UnreadCountOut(BaseModel):
    count: int


class DuesReminderRequest(BaseModel):
    member_id: int | None = None
    all_outstanding: bool = False
    branch_id: int | None = None


class DuesReminderResult(BaseModel):
    sent_count: int


class ActivityReminderRequest(BaseModel):
    activity_id: int = Field(gt=0)


class ActivityReminderResult(BaseModel):
    sent_count: int
