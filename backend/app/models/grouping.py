import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class GroupStatus(str, enum.Enum):
    scheduled = "scheduled"
    playing = "playing"
    completed = "completed"


class CompetitionGroup(Base, AuditMixin):
    """赛事分组：一组对应一个 Tee Time / 出发洞。"""

    __tablename__ = "competition_groups"

    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"), nullable=False, index=True
    )
    group_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tee_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    starting_hole: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[GroupStatus] = mapped_column(
        Enum(GroupStatus, name="group_status", native_enum=False, length=16),
        default=GroupStatus.scheduled,
        nullable=False,
        index=True,
    )


class CompetitionGroupPlayer(Base, AuditMixin):
    """分组球员：记录分组时刻的差点/球队快照，供分组算法溯源与页面展示。"""

    __tablename__ = "competition_group_players"

    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"), nullable=False, index=True
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("competition_groups.id"), nullable=False, index=True
    )
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False, index=True)
    registration_id: Mapped[int | None] = mapped_column(
        ForeignKey("competition_registrations.id"), nullable=True, index=True
    )
    order_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # 分组时刻快照，不随会员后续差点调整变化
    handicap: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"), nullable=True, index=True
    )
