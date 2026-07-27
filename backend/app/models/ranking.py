import enum
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class RankingScope(str, enum.Enum):
    individual = "individual"
    team = "team"


class Ranking(Base, AuditMixin):
    """赛事排名：发布时整体替换（软删旧行+插入新行）。"""

    __tablename__ = "rankings"

    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"), nullable=False, index=True
    )
    scope: Mapped[RankingScope] = mapped_column(
        Enum(RankingScope, name="ranking_scope", native_enum=False, length=16),
        nullable=False,
        index=True,
    )
    member_id: Mapped[int | None] = mapped_column(
        ForeignKey("members.id"), nullable=True, index=True
    )
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(6, 1), nullable=False)
    award: Mapped[str | None] = mapped_column(String(64), nullable=True)
