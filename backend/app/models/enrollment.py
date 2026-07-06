import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class EnrollmentStatus(str, enum.Enum):
    pending_captain = "pending_captain"  # 待队长审核
    pending_branch = "pending_branch"    # 队长通过，待分会备案
    approved = "approved"                # 分会备案通过，正式入队
    rejected = "rejected"                # 被驳回


class TeamEnrollment(Base, AuditMixin):
    """球队入队审批流：会员申请 → 队长审核 → 分会备案。"""

    __tablename__ = "team_enrollments"

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[EnrollmentStatus] = mapped_column(
        Enum(EnrollmentStatus, name="enrollment_status", native_enum=False, length=24),
        default=EnrollmentStatus.pending_captain,
        nullable=False,
        index=True,
    )

    captain_reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    captain_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    branch_reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    branch_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    remark: Mapped[str | None] = mapped_column(String(512), nullable=True)
