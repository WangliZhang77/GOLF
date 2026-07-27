from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class Course(Base, AuditMixin):
    """球场档案：Phase 8 建表时的基础字段 + Phase 14 补充的球场参数字段（city/holes/par/rating/slope）。
    球场可用性/球位预订等仍留待后续阶段，不做推倒重来。"""

    __tablename__ = "courses"

    name_zh: Mapped[str] = mapped_column(String(128), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    city: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    holes: Mapped[int | None] = mapped_column(Integer, nullable=True, default=18)
    par: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    slope: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
