from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class Team(Base, AuditMixin):
    """球队主表：归属某个分会。"""

    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    branch_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    captain_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    founded_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    home_course: Mapped[str | None] = mapped_column(String(128), nullable=True)
    logo: Mapped[str | None] = mapped_column(String(512), nullable=True)
    charter: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
