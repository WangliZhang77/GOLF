from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.finance import (
    DUES_CATEGORIES,
    FinanceLedger,
    IncomeCategory,
    LedgerDirection,
    LedgerStatus,
)
from app.models.member import Member
from app.models.user import User, UserRole
from app.schemas.finance import (
    LedgerCreate,
    LedgerOut,
    LedgerSummary,
    RefundRequest,
    VoidRequest,
)

router = APIRouter(prefix="/finance", tags=["finance"])

_WRITE_ROLES = {UserRole.super_admin, UserRole.finance}
_READ_ROLES = {UserRole.super_admin, UserRole.finance, UserRole.council_admin}


def _get_ledger(db: Session, ledger_id: int) -> FinanceLedger:
    row = (
        db.query(FinanceLedger)
        .filter(FinanceLedger.id == ledger_id, FinanceLedger.is_deleted.is_(False))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="流水不存在 / Ledger not found")
    return row


def _assert_read_scope(row: FinanceLedger, user: User) -> None:
    if user.role in {UserRole.super_admin, UserRole.finance}:
        return
    if user.role == UserRole.council_admin and user.branch_id:
        if row.branch_id is None or row.branch_id == user.branch_id:
            return
    raise HTTPException(status_code=403, detail="权限不足 / Forbidden")


def _ledger_query_for_user(db: Session, user: User):
    q = db.query(FinanceLedger).filter(FinanceLedger.is_deleted.is_(False))
    if user.role in {UserRole.super_admin, UserRole.finance}:
        return q
    if user.role == UserRole.council_admin and user.branch_id:
        return q.filter(
            (FinanceLedger.branch_id == user.branch_id)
            | (FinanceLedger.branch_id.is_(None))
        )
    return q.filter(False)


def _assert_active(row: FinanceLedger) -> None:
    if row.status != LedgerStatus.confirmed:
        raise HTTPException(
            status_code=400,
            detail="流水已作废或已退款 / Ledger voided or refunded",
        )


@router.post("/ledger", response_model=LedgerOut, status_code=status.HTTP_201_CREATED)
def create_ledger(
    body: LedgerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.super_admin, UserRole.finance)),
):
    row = FinanceLedger(
        direction=body.direction,
        category=body.category,
        amount=body.amount,
        currency=body.currency,
        title=body.title,
        remark=body.remark,
        member_id=body.member_id,
        branch_id=body.branch_id,
        activity_id=body.activity_id,
        is_paid=body.is_paid if body.direction == LedgerDirection.income else True,
        payment_method=body.payment_method,
        created_by=current_user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/ledger/summary", response_model=LedgerSummary)
def ledger_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.super_admin, UserRole.finance)),
):
    q = _ledger_query_for_user(db, current_user)
    confirmed = q.filter(FinanceLedger.status == LedgerStatus.confirmed)

    income = (
        confirmed.filter(
            FinanceLedger.direction == LedgerDirection.income,
            FinanceLedger.refund_of_id.is_(None),
        )
        .with_entities(func.coalesce(func.sum(FinanceLedger.amount), 0))
        .scalar()
    )
    expense = (
        confirmed.filter(FinanceLedger.direction == LedgerDirection.expense)
        .with_entities(func.coalesce(func.sum(FinanceLedger.amount), 0))
        .scalar()
    )
    voided_count = q.filter(FinanceLedger.status == LedgerStatus.voided).count()
    unreconciled_count = confirmed.filter(FinanceLedger.reconciled.is_(False)).count()

    income_d = Decimal(str(income or 0))
    expense_d = Decimal(str(expense or 0))
    return LedgerSummary(
        total_income=income_d,
        total_expense=expense_d,
        net=income_d - expense_d,
        voided_count=voided_count,
        unreconciled_count=unreconciled_count,
    )


@router.get("/ledger", response_model=list[LedgerOut])
def list_ledger(
    direction: LedgerDirection | None = None,
    category: str | None = None,
    member_id: int | None = None,
    reconciled: bool | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.super_admin, UserRole.finance, UserRole.council_admin
        )
    ),
):
    q = _ledger_query_for_user(db, current_user)
    if direction:
        q = q.filter(FinanceLedger.direction == direction)
    if category:
        q = q.filter(FinanceLedger.category == category)
    if member_id is not None:
        q = q.filter(FinanceLedger.member_id == member_id)
    if reconciled is not None:
        q = q.filter(FinanceLedger.reconciled.is_(reconciled))
    return q.order_by(FinanceLedger.id.desc()).all()


@router.get("/ledger/{ledger_id}", response_model=LedgerOut)
def get_ledger(
    ledger_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.super_admin, UserRole.finance, UserRole.council_admin
        )
    ),
):
    row = _get_ledger(db, ledger_id)
    _assert_read_scope(row, current_user)
    return row


@router.post("/ledger/{ledger_id}/void", response_model=LedgerOut)
def void_ledger(
    ledger_id: int,
    body: VoidRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.super_admin, UserRole.finance)),
):
    row = _get_ledger(db, ledger_id)
    if row.status != LedgerStatus.confirmed:
        raise HTTPException(status_code=400, detail="仅可作废已确认流水 / Only confirmed")
    row.status = LedgerStatus.voided
    row.void_reason = body.reason
    row.voided_by = current_user.id
    row.voided_at = datetime.now(timezone.utc)
    row.updated_by = current_user.id
    db.commit()
    db.refresh(row)
    return row


@router.post("/ledger/{ledger_id}/reconcile", response_model=LedgerOut)
def reconcile_ledger(
    ledger_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.super_admin, UserRole.finance)),
):
    row = _get_ledger(db, ledger_id)
    _assert_active(row)
    row.reconciled = True
    row.reconciled_by = current_user.id
    row.reconciled_at = datetime.now(timezone.utc)
    row.updated_by = current_user.id
    db.commit()
    db.refresh(row)
    return row


@router.post("/ledger/{ledger_id}/mark-paid", response_model=LedgerOut)
def mark_paid(
    ledger_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.super_admin, UserRole.finance)),
):
    row = _get_ledger(db, ledger_id)
    _assert_active(row)
    if row.direction != LedgerDirection.income:
        raise HTTPException(status_code=400, detail="仅收入流水可标记已收 / Income only")
    try:
        cat = IncomeCategory(row.category)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效收入分类 / Invalid category")
    if cat not in DUES_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail="仅会费/报名费可标记已收 / Dues or registration only",
        )
    row.is_paid = True
    row.updated_by = current_user.id
    db.commit()
    db.refresh(row)
    return row


@router.post("/ledger/{ledger_id}/refund", response_model=LedgerOut)
def refund_ledger(
    ledger_id: int,
    body: RefundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.super_admin, UserRole.finance)),
):
    original = _get_ledger(db, ledger_id)
    if original.status != LedgerStatus.confirmed:
        raise HTTPException(status_code=400, detail="仅可退款已确认流水 / Only confirmed")
    if original.direction != LedgerDirection.income:
        raise HTTPException(status_code=400, detail="仅收入流水可退款 / Income only")

    refund_amount = body.amount if body.amount is not None else original.amount
    if refund_amount > original.amount:
        raise HTTPException(status_code=400, detail="退款额不能超过原额 / Amount too large")

    original.status = LedgerStatus.refunded
    original.updated_by = current_user.id

    refund_row = FinanceLedger(
        direction=LedgerDirection.income,
        category=original.category,
        amount=refund_amount,
        currency=original.currency,
        title=f"退款 #{original.id}: {original.title}",
        remark=body.remark or original.remark,
        member_id=original.member_id,
        branch_id=original.branch_id,
        activity_id=original.activity_id,
        is_paid=True,
        payment_method=original.payment_method,
        refund_of_id=original.id,
        created_by=current_user.id,
    )
    db.add(refund_row)
    db.commit()
    db.refresh(refund_row)
    return refund_row


@router.get("/me/bills", response_model=list[LedgerOut])
def my_bills(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    member = (
        db.query(Member)
        .filter(Member.user_id == current_user.id, Member.is_deleted.is_(False))
        .first()
    )
    if member is None:
        return []

    return (
        db.query(FinanceLedger)
        .filter(
            FinanceLedger.member_id == member.id,
            FinanceLedger.is_deleted.is_(False),
            FinanceLedger.direction == LedgerDirection.income,
        )
        .order_by(FinanceLedger.id.desc())
        .all()
    )
