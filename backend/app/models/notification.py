import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class MessageType(str, enum.Enum):
    activity_registered = "activity_registered"
    dues_reminder = "dues_reminder"
    activity_reminder = "activity_reminder"
    system = "system"
    score_published = "score_published"


class Notification(Base, AuditMixin):
    """站内消息（双语；禁止在正文中携带隐私字段）。"""

    __tablename__ = "notifications"

    recipient_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType, name="message_type", native_enum=False, length=24),
        nullable=False,
        index=True,
    )

    title_zh: Mapped[str] = mapped_column(String(128), nullable=False)
    title_en: Mapped[str] = mapped_column(String(128), nullable=False)
    body_zh: Mapped[str] = mapped_column(Text, nullable=False)
    body_en: Mapped[str] = mapped_column(Text, nullable=False)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    related_member_id: Mapped[int | None] = mapped_column(
        ForeignKey("members.id"), nullable=True, index=True
    )
    related_activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id"), nullable=True, index=True
    )
    related_ledger_id: Mapped[int | None] = mapped_column(
        ForeignKey("finance_ledger.id"), nullable=True, index=True
    )

    sent_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
