from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.models.finance import FinanceLedger, LedgerDirection, LedgerStatus
from app.services.billing import member_has_outstanding
from tests.conftest import auth


def _ledger_payload(**overrides):
    base = {
        "direction": "income",
        "category": "annual_dues",
        "amount": "120.00",
        "title": "2026 年度会费",
        "member_id": None,
        "branch_id": None,
        "is_paid": False,
    }
    base.update(overrides)
    return base


def _create_member(client, world, **overrides):
    payload = {
        "chinese_name": "财务测试",
        "english_name": "Finance Test",
        "branch_id": world["branch_a"].id,
        "passport_no": "FIN123456",
        "local_phone": "+64219999999",
        "level": "probationary",
    }
    payload.update(overrides)
    return client.post("/api/members", json=payload, headers=auth(world["super"]))


class TestFinanceCrud:
    def test_finance_can_create_income_and_expense(self, client, world):
        inc = client.post(
            "/api/finance/ledger",
            json=_ledger_payload(),
            headers=auth(world["finance"]),
        )
        assert inc.status_code == 201, inc.text
        assert inc.json()["direction"] == "income"

        exp = client.post(
            "/api/finance/ledger",
            json={
                "direction": "expense",
                "category": "admin_expense",
                "amount": "50.00",
                "title": "办公用品",
            },
            headers=auth(world["finance"]),
        )
        assert exp.status_code == 201
        assert exp.json()["direction"] == "expense"

    def test_member_cannot_create_ledger(self, client, world):
        resp = client.post(
            "/api/finance/ledger",
            json=_ledger_payload(),
            headers=auth(world["member"]),
        )
        assert resp.status_code == 403


class TestFinanceOps:
    def test_void_keeps_record(self, client, world):
        lid = client.post(
            "/api/finance/ledger",
            json=_ledger_payload(),
            headers=auth(world["finance"]),
        ).json()["id"]

        voided = client.post(
            f"/api/finance/ledger/{lid}/void",
            json={"reason": "录入错误"},
            headers=auth(world["finance"]),
        )
        assert voided.status_code == 200
        assert voided.json()["status"] == "voided"

        still = client.get(
            f"/api/finance/ledger/{lid}", headers=auth(world["finance"])
        )
        assert still.status_code == 200
        assert still.json()["id"] == lid

    def test_refund_creates_linked_entry(self, client, world):
        lid = client.post(
            "/api/finance/ledger",
            json=_ledger_payload(is_paid=True),
            headers=auth(world["finance"]),
        ).json()["id"]

        refund = client.post(
            f"/api/finance/ledger/{lid}/refund",
            json={"amount": "30.00", "remark": "部分退款"},
            headers=auth(world["finance"]),
        )
        assert refund.status_code == 200
        body = refund.json()
        assert body["refund_of_id"] == lid

        original = client.get(
            f"/api/finance/ledger/{lid}", headers=auth(world["finance"])
        ).json()
        assert original["status"] == "refunded"

    def test_reconcile_marks_ledger(self, client, world):
        lid = client.post(
            "/api/finance/ledger",
            json=_ledger_payload(),
            headers=auth(world["finance"]),
        ).json()["id"]

        rec = client.post(
            f"/api/finance/ledger/{lid}/reconcile",
            headers=auth(world["finance"]),
        )
        assert rec.status_code == 200
        assert rec.json()["reconciled"] is True


class TestBillingAndPromote:
    def test_member_has_outstanding(self, client, world, db):
        mid = _create_member(client, world).json()["id"]
        assert member_has_outstanding(db, mid) is False

        client.post(
            "/api/finance/ledger",
            json=_ledger_payload(member_id=mid, is_paid=False),
            headers=auth(world["finance"]),
        )
        db.expire_all()
        assert member_has_outstanding(db, mid) is True

    def test_promote_blocked_by_outstanding_dues(self, client, world, db):
        from app.models.activity import (
            Activity,
            ActivityRegistration,
            ActivityStatus,
            ActivityType,
            RegistrantType,
            RegistrationStatus,
        )

        old = (date.today() - timedelta(days=200)).isoformat()
        mid = _create_member(client, world, join_date=old).json()["id"]

        for i in range(5):
            act = Activity(
                title=f"出勤{i}",
                activity_type=ActivityType.weekly_round,
                status=ActivityStatus.closed,
                branch_id=world["branch_a"].id,
                start_at=datetime.now(timezone.utc),
                max_participants=10,
                created_by=world["super"].id,
            )
            db.add(act)
            db.flush()
            db.add(
                ActivityRegistration(
                    activity_id=act.id,
                    member_id=mid,
                    user_id=world["super"].id,
                    registrant_type=RegistrantType.member,
                    status=RegistrationStatus.checked_in,
                    created_by=world["super"].id,
                )
            )
        db.commit()

        client.post(
            "/api/finance/ledger",
            json=_ledger_payload(member_id=mid, is_paid=False),
            headers=auth(world["finance"]),
        )

        resp = client.post(f"/api/members/{mid}/promote", headers=auth(world["super"]))
        assert resp.status_code == 200
        assert resp.json()["promoted"] is False
        assert "欠费" in resp.json()["reason"] or "Outstanding" in resp.json()["reason"]


class TestMyBills:
    def test_me_bills_only_own(self, client, world):
        created = _create_member(
            client, world, account_username="billuser", account_password="pw123456"
        ).json()
        mid = created["id"]
        uid = created["user_id"]

        client.post(
            "/api/finance/ledger",
            json=_ledger_payload(member_id=mid),
            headers=auth(world["finance"]),
        )
        other_mid = _create_member(client, world, chinese_name="他人").json()["id"]
        client.post(
            "/api/finance/ledger",
            json=_ledger_payload(member_id=other_mid, title="他人会费"),
            headers=auth(world["finance"]),
        )

        from app.core.security import create_access_token

        bills = client.get(
            "/api/finance/me/bills",
            headers={"Authorization": f"Bearer {create_access_token(uid)}"},
        )
        assert bills.status_code == 200
        assert len(bills.json()) == 1
        assert bills.json()[0]["member_id"] == mid


class TestSummary:
    def test_summary_excludes_voided(self, client, world):
        client.post(
            "/api/finance/ledger",
            json=_ledger_payload(amount="100.00", is_paid=True),
            headers=auth(world["finance"]),
        )
        void_id = client.post(
            "/api/finance/ledger",
            json=_ledger_payload(amount="200.00", title="待作废"),
            headers=auth(world["finance"]),
        ).json()["id"]
        client.post(
            f"/api/finance/ledger/{void_id}/void",
            json={"reason": "测试"},
            headers=auth(world["finance"]),
        )
        client.post(
            "/api/finance/ledger",
            json={
                "direction": "expense",
                "category": "admin_expense",
                "amount": "40.00",
                "title": "支出",
            },
            headers=auth(world["finance"]),
        )

        summary = client.get(
            "/api/finance/ledger/summary", headers=auth(world["finance"])
        )
        assert summary.status_code == 200
        body = summary.json()
        assert Decimal(body["total_income"]) == Decimal("100.00")
        assert Decimal(body["total_expense"]) == Decimal("40.00")
        assert Decimal(body["net"]) == Decimal("60.00")
        assert body["voided_count"] >= 1
