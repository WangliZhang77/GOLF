from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.finance import (
    ExpenseCategory,
    IncomeCategory,
    LedgerDirection,
    LedgerStatus,
    PaymentMethod,
)


class LedgerCreate(BaseModel):
    direction: LedgerDirection
    category: str
    amount: Decimal = Field(gt=0)
    currency: str = "NZD"
    title: str
    remark: str | None = None
    member_id: int | None = None
    branch_id: int | None = None
    activity_id: int | None = None
    is_paid: bool = False
    payment_method: PaymentMethod = PaymentMethod.manual

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str, info):
        direction = info.data.get("direction")
        if direction == LedgerDirection.income:
            IncomeCategory(v)
        elif direction == LedgerDirection.expense:
            ExpenseCategory(v)
        return v


class LedgerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    direction: LedgerDirection
    category: str
    amount: Decimal
    currency: str
    title: str
    remark: str | None
    member_id: int | None
    branch_id: int | None
    activity_id: int | None
    status: LedgerStatus
    is_paid: bool
    payment_method: PaymentMethod
    void_reason: str | None
    voided_by: int | None
    voided_at: datetime | None
    reconciled: bool
    reconciled_by: int | None
    reconciled_at: datetime | None
    refund_of_id: int | None
    created_at: datetime
    created_by: int | None


class VoidRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=512)


class RefundRequest(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    remark: str | None = None


class LedgerSummary(BaseModel):
    total_income: Decimal
    total_expense: Decimal
    net: Decimal
    voided_count: int
    unreconciled_count: int
