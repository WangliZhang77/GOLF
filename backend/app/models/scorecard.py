import enum
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base

HOLE_COUNT = 18


class ScoreCardStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    checking = "checking"
    approved = "approved"
    rejected = "rejected"


class ScoreReviewStatus(str, enum.Enum):
    submitted = "submitted"
    checking = "checking"
    approved = "approved"
    rejected = "rejected"


class ScoreCard(Base, AuditMixin):
    """18洞计分卡：一人一赛事一张。差点为开赛时刻快照，不随后续差点调整变化。"""

    __tablename__ = "score_cards"

    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id"), nullable=False, index=True
    )
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), nullable=False, index=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("competition_groups.id"), nullable=False, index=True
    )

    hole1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole3: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole4: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole5: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole6: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole7: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole8: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole9: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole10: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole11: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole12: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole13: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole14: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole15: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole16: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole17: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hole18: Mapped[int | None] = mapped_column(Integer, nullable=True)

    out_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    in_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 开赛时刻（POST /start）从 CompetitionGroupPlayer.handicap 快照，不随后续差点调整变化
    handicap_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    net_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)

    status: Mapped[ScoreCardStatus] = mapped_column(
        Enum(ScoreCardStatus, name="score_card_status", native_enum=False, length=16),
        default=ScoreCardStatus.draft,
        nullable=False,
        index=True,
    )


class ScoreReview(Base, AuditMixin):
    """成绩审核动作日志：每次同组确认/管理员审核各插入一行，不覆盖历史记录。"""

    __tablename__ = "score_reviews"

    score_id: Mapped[int] = mapped_column(ForeignKey("score_cards.id"), nullable=False, index=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[ScoreReviewStatus] = mapped_column(
        Enum(ScoreReviewStatus, name="score_review_status", native_enum=False, length=16),
        nullable=False,
        index=True,
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
