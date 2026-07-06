import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class LedgerDirection(str, enum.Enum):
    income = "income"
    expense = "expense"


class IncomeCategory(str, enum.Enum):
    annual_dues = "annual_dues"
    event_registration = "event_registration"
    sponsorship = "sponsorship"
    course_subsidy = "course_subsidy"
    donation = "donation"
    other = "other"


class ExpenseCategory(str, enum.Enum):
    course_fee = "course_fee"
    event_supplies = "event_supplies"
    referee_subsidy = "referee_subsidy"
    trophy_prize = "trophy_prize"
    admin_expense = "admin_expense"
    payment_fee = "payment_fee"
    other = "other"


class LedgerStatus(str, enum.Enum):
    confirmed = "confirmed"
    voided = "voided"
    refunded = "refunded"


class PaymentMethod(str, enum.Enum):
    manual = "manual"
    cash = "cash"
    bank_transfer = "bank_transfer"


# 会费/报名费类收入，用于欠费判定
DUES_CATEGORIES = {IncomeCategory.annual_dues, IncomeCategory.event_registration}


class FinanceLedger(Base, AuditMixin):
    """财务流水表（方案：收支、对账、退款标记；不可物理删除）。"""

    __tablename__ = "finance_ledger"

    direction: Mapped[LedgerDirection] = mapped_column(
        Enum(LedgerDirection, name="ledger_direction", native_enum=False, length=16),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="NZD", nullable=False)

    member_id: Mapped[int | None] = mapped_column(
        ForeignKey("members.id"), nullable=True, index=True
    )
    branch_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id"), nullable=True, index=True
    )

    title: Mapped[str] = mapped_column(String(128), nullable=False)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[LedgerStatus] = mapped_column(
        Enum(LedgerStatus, name="ledger_status", native_enum=False, length=16),
        default=LedgerStatus.confirmed,
        nullable=False,
        index=True,
    )
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method", native_enum=False, length=16),
        default=PaymentMethod.manual,
        nullable=False,
    )

    void_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    voided_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    reconciled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reconciled_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    refund_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("finance_ledger.id"), nullable=True, index=True
    )
