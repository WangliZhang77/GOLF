import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class MemberLevel(str, enum.Enum):
    honorary = "honorary"          # 荣誉会员
    formal = "formal"              # 正式会员
    probationary = "probationary"  # 预备会员
    blacklist = "blacklist"        # 黑名单


class MemberStatus(str, enum.Enum):
    active = "active"        # 正常
    sleeping = "sleeping"    # 沉睡会员
    cancelled = "cancelled"  # 已注销


class Member(Base, AuditMixin):
    """会员主表（全系统数据源头）。公开信息与隐私信息分级存储。"""

    __tablename__ = "members"

    # 关联登录账号（可空：也允许先建档后开通账号）
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, unique=True, index=True
    )

    # -------- 公开信息 --------
    chinese_name: Mapped[str] = mapped_column(String(64), nullable=False)
    english_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(512), nullable=True)
    golf_age: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 球龄
    club_number: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 球杆号码
    # 差点（V1.5 计分模块联动，这里先预留字段不做业务逻辑）
    handicap: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)

    # -------- 隐私信息（仅超管/财务可见，合规加密/脱敏后置到合规阶段）--------
    nz_address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    local_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    passport_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    visa_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_account: Mapped[str | None] = mapped_column(String(128), nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # -------- 等级/状态/归属 --------
    level: Mapped[MemberLevel] = mapped_column(
        Enum(MemberLevel, name="member_level", native_enum=False, length=16),
        default=MemberLevel.probationary,
        nullable=False,
        index=True,
    )
    status: Mapped[MemberStatus] = mapped_column(
        Enum(MemberStatus, name="member_status", native_enum=False, length=16),
        default=MemberStatus.active,
        nullable=False,
        index=True,
    )
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True, index=True
    )

    join_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
