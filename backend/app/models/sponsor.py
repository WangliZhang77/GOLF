from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class Sponsor(Base, AuditMixin):
    """赞助商档案：企业合作方，非分会归属（协会层面的合作关系）。"""

    __tablename__ = "sponsors"

    company_name: Mapped[str] = mapped_column(String(128), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    website: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # 赞助等级：自由文本（如"金牌"/"银牌"），暂无固定分级表，同 Competition.level 的处理方式
    level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)


class SponsorContract(Base, AuditMixin):
    """赞助合同：可关联具体赛事，也可为不挂靠单个赛事的年度/一般性赞助。"""

    __tablename__ = "sponsor_contracts"

    sponsor_id: Mapped[int] = mapped_column(ForeignKey("sponsors.id"), nullable=False, index=True)
    competition_id: Mapped[int | None] = mapped_column(
        ForeignKey("competitions.id"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    benefit: Mapped[str | None] = mapped_column(Text, nullable=True)
