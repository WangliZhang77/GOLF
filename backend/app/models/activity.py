import enum
import secrets
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class ActivityType(str, enum.Enum):
    """方案模块3：活动类型。"""

    weekly_round = "weekly_round"      # 每周例行下场
    team_building = "team_building"    # 华人高尔夫团建
    course_visit = "course_visit"      # 球场交流访学
    networking = "networking"          # 行业联谊
    newbie_salon = "newbie_salon"      # 新人教学沙龙


class ActivityStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    closed = "closed"
    cancelled = "cancelled"


class RegistrantType(str, enum.Enum):
    member = "member"   # 会员本人
    family = "family"   # 随行家属


class RegistrationStatus(str, enum.Enum):
    registered = "registered"
    checked_in = "checked_in"
    absent = "absent"
    cancelled = "cancelled"


def _new_checkin_token() -> str:
    return secrets.token_urlsafe(16)


class Activity(Base, AuditMixin):
    """日常下场与非竞技活动（与赛事计分数据隔离）。"""

    __tablename__ = "activities"

    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    activity_type: Mapped[ActivityType] = mapped_column(
        Enum(ActivityType, name="activity_type", native_enum=False, length=24),
        nullable=False,
        index=True,
    )
    status: Mapped[ActivityStatus] = mapped_column(
        Enum(ActivityStatus, name="activity_status", native_enum=False, length=16),
        default=ActivityStatus.draft,
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True, index=True
    )

    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    course_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 报名管控：会员名额 + 家属名额分开统计
    max_participants: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    max_family_slots: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    family_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    course_slots_locked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # 扫码签到令牌（管理员展示二维码，会员端携带 token 签到）
    checkin_token: Mapped[str] = mapped_column(
        String(32), default=_new_checkin_token, nullable=False, index=True
    )

    # 简易记分：日常活动仅记录总杆，不联动官方差点（V1.5 赛事模块隔离）
    simple_scoring_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )


class ActivityRegistration(Base, AuditMixin):
    """活动报名表：会员与随行家属分行记录，便于单独统计。"""

    __tablename__ = "activity_registrations"

    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id"), nullable=False, index=True
    )
    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )

    registrant_type: Mapped[RegistrantType] = mapped_column(
        Enum(RegistrantType, name="registrant_type", native_enum=False, length=16),
        nullable=False,
        index=True,
    )
    family_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    family_relation: Mapped[str | None] = mapped_column(String(32), nullable=True)

    status: Mapped[RegistrationStatus] = mapped_column(
        Enum(RegistrationStatus, name="registration_status", native_enum=False, length=16),
        default=RegistrationStatus.registered,
        nullable=False,
        index=True,
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 简易记分：仅总杆，不联动差点
    total_strokes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)
