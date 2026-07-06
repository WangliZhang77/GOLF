"""会费/欠费判定，供转正与后续催缴复用。"""

from sqlalchemy.orm import Session

from app.models.finance import (
    DUES_CATEGORIES,
    FinanceLedger,
    IncomeCategory,
    LedgerDirection,
    LedgerStatus,
)


def member_has_outstanding(db: Session, member_id: int) -> bool:
    """是否存在未缴清的会费/报名费流水。"""
    rows = (
        db.query(FinanceLedger)
        .filter(
            FinanceLedger.member_id == member_id,
            FinanceLedger.direction == LedgerDirection.income,
            FinanceLedger.status == LedgerStatus.confirmed,
            FinanceLedger.is_paid.is_(False),
            FinanceLedger.is_deleted.is_(False),
        )
        .all()
    )
    for row in rows:
        try:
            if IncomeCategory(row.category) in DUES_CATEGORIES:
                return True
        except ValueError:
            continue
    return False


def list_member_outstanding_ledgers(db: Session, member_id: int) -> list[FinanceLedger]:
    """返回会员未缴清的会费/报名费流水。"""
    rows = (
        db.query(FinanceLedger)
        .filter(
            FinanceLedger.member_id == member_id,
            FinanceLedger.direction == LedgerDirection.income,
            FinanceLedger.status == LedgerStatus.confirmed,
            FinanceLedger.is_paid.is_(False),
            FinanceLedger.is_deleted.is_(False),
        )
        .all()
    )
    result: list[FinanceLedger] = []
    for row in rows:
        try:
            if IncomeCategory(row.category) in DUES_CATEGORIES:
                result.append(row)
        except ValueError:
            continue
    return result


def list_outstanding_member_ids(
    db: Session, branch_id: int | None = None
) -> list[int]:
    """有欠费的会员 ID 列表（可筛分会）。"""
    q = db.query(FinanceLedger.member_id).filter(
        FinanceLedger.member_id.isnot(None),
        FinanceLedger.direction == LedgerDirection.income,
        FinanceLedger.status == LedgerStatus.confirmed,
        FinanceLedger.is_paid.is_(False),
        FinanceLedger.is_deleted.is_(False),
    )
    if branch_id is not None:
        q = q.filter(FinanceLedger.branch_id == branch_id)
    ids: set[int] = set()
    for (mid,) in q.distinct().all():
        if mid is not None and member_has_outstanding(db, mid):
            ids.add(mid)
    return sorted(ids)
