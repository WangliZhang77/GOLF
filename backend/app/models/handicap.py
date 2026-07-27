import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class HandicapSource(str, enum.Enum):
    manual = "manual"              # 人工维护（Phase 13 一期）
    competition = "competition"    # 根据赛事成绩推算（预留，未接入）
    nz_golf_api = "nz_golf_api"    # NZ Golf 官方接口（预留，未接入）


class HandicapHistory(Base, AuditMixin):
    """差点变更历史：每次调整插入一行，不覆盖。"""

    __tablename__ = "handicap_history"

    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    old_handicap: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    new_handicap: Mapped[Decimal] = mapped_column(Numeric(4, 1), nullable=False)
    source: Mapped[HandicapSource] = mapped_column(
        Enum(HandicapSource, name="handicap_source", native_enum=False, length=16),
        nullable=False,
        index=True,
    )
    competition_id: Mapped[int | None] = mapped_column(
        ForeignKey("competitions.id"), nullable=True, index=True
    )
    remark: Mapped[str | None] = mapped_column(String(256), nullable=True)
