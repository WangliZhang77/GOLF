import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class CompetitionType(str, enum.Enum):
    """Phase 8：赛事类型。与 Activity 的活动类型枚举完全隔离，互不复用。"""

    official = "official"        # 协会正式赛事
    team = "team"                # 球队比赛
    invitation = "invitation"    # 邀请赛
    social = "social"            # 社交比赛
    training = "training"        # 培训活动


class CompetitionStatus(str, enum.Enum):
    draft = "draft"
    open = "open"
    closed = "closed"
    playing = "playing"
    review = "review"
    completed = "completed"
    cancelled = "cancelled"


class CompetitionRegPaymentStatus(str, enum.Enum):
    unpaid = "unpaid"
    paid = "paid"
    waived = "waived"


class CompetitionRegApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class Competition(Base, AuditMixin):
    """赛事表：官方赛事/球队比赛/邀请赛/社交比赛/培训活动。
    分组/计分/排名/历史归档留待方案后续章节到齐后再建（Phase 8 后续迭代）。"""

    __tablename__ = "competitions"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    competition_type: Mapped[CompetitionType] = mapped_column(
        Enum(CompetitionType, name="competition_type", native_enum=False, length=16),
        nullable=False,
        index=True,
    )
    # 赛事等级：如"A级"，暂无固定分级表，先用自由文本，避免过早枚举化
    level: Mapped[str | None] = mapped_column(String(32), nullable=True)

    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id"), nullable=True, index=True
    )
    # 可空 = 总会级/跨分会赛事；非空 = 仅该分会
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )

    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registration_deadline: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    fee: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    max_players: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    # 差点上限：报名资格闸门，留空表示不限差点
    max_handicap: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)

    status: Mapped[CompetitionStatus] = mapped_column(
        Enum(CompetitionStatus, name="competition_status", native_enum=False, length=16),
        default=CompetitionStatus.draft,
        nullable=False,
        index=True,
    )


class CompetitionRegistration(Base, AuditMixin):
    """赛事报名表：一人一行；team_id 报名时由会员自身 team_id 自动带入，不接受前端指定。"""

    __tablename__ = "competition_registrations"

    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"), nullable=False, index=True
    )
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)

    registration_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    payment_status: Mapped[CompetitionRegPaymentStatus] = mapped_column(
        Enum(
            CompetitionRegPaymentStatus,
            name="competition_reg_payment_status",
            native_enum=False,
            length=16,
        ),
        default=CompetitionRegPaymentStatus.unpaid,
        nullable=False,
        index=True,
    )
    approval_status: Mapped[CompetitionRegApprovalStatus] = mapped_column(
        Enum(
            CompetitionRegApprovalStatus,
            name="competition_reg_approval_status",
            native_enum=False,
            length=16,
        ),
        default=CompetitionRegApprovalStatus.pending,
        nullable=False,
        index=True,
    )
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)
