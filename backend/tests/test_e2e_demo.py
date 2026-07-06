"""端到端主链路：会员生命周期 + 财务催缴 + 活动报名消息联动。

覆盖 Phase 3~6 的跨模块打通，作为 Phase 7 联调的自动化回归。
"""

from datetime import date, datetime, timedelta, timezone

from app.core.security import create_access_token
from app.models.activity import (
    Activity,
    ActivityRegistration,
    ActivityStatus,
    ActivityType,
    RegistrantType,
    RegistrationStatus,
)
from tests.conftest import auth


def _token(uid: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(uid)}"}


class TestE2EDemoFlow:
    def test_member_lifecycle_finance_and_messages(self, client, world, db):
        # 1. 建预备会员（入会满 3 个月），并开通登录账号
        join_date = (date.today() - timedelta(days=120)).isoformat()
        created = client.post(
            "/api/members",
            json={
                "chinese_name": "端到端会员",
                "english_name": "E2E Member",
                "branch_id": world["branch_a"].id,
                "passport_no": "E2E-PRIV-001",
                "local_phone": "+64217777777",
                "level": "probationary",
                "join_date": join_date,
                "account_username": "e2e_member",
                "account_password": "pw123456",
            },
            headers=auth(world["super"]),
        )
        assert created.status_code == 201, created.text
        member = created.json()
        mid = member["id"]
        uid = member["user_id"]
        assert uid is not None

        # 2. 模拟 5 次历史签到，满足出勤门槛
        for i in range(5):
            act = Activity(
                title=f"E2E 出勤 {i}",
                activity_type=ActivityType.weekly_round,
                status=ActivityStatus.closed,
                branch_id=world["branch_a"].id,
                start_at=datetime.now(timezone.utc) - timedelta(days=(i + 1) * 7),
                max_participants=10,
                created_by=world["super"].id,
            )
            db.add(act)
            db.flush()
            db.add(
                ActivityRegistration(
                    activity_id=act.id,
                    member_id=mid,
                    user_id=uid,
                    registrant_type=RegistrantType.member,
                    status=RegistrationStatus.checked_in,
                    created_by=world["super"].id,
                )
            )
        db.commit()

        # 3. 财务记一笔待缴会费
        ledger = client.post(
            "/api/finance/ledger",
            json={
                "direction": "income",
                "category": "annual_dues",
                "amount": "120.00",
                "title": "2026 年度会费",
                "member_id": mid,
                "is_paid": False,
            },
            headers=auth(world["finance"]),
        )
        assert ledger.status_code == 201, ledger.text
        ledger_id = ledger.json()["id"]

        # 4. 转正应因欠费失败
        promote_fail = client.post(
            f"/api/members/{mid}/promote", headers=auth(world["super"])
        )
        assert promote_fail.status_code == 200
        assert promote_fail.json()["promoted"] is False

        # 5. 财务催缴 → 会员收到催缴站内信（不含隐私）
        reminder = client.post(
            "/api/messages/dues-reminder",
            json={"member_id": mid},
            headers=auth(world["finance"]),
        )
        assert reminder.status_code == 200
        assert reminder.json()["sent_count"] >= 1

        inbox = client.get("/api/messages/me", headers=_token(uid)).json()
        dues_msgs = [m for m in inbox if m["message_type"] == "dues_reminder"]
        assert len(dues_msgs) >= 1
        assert "E2E-PRIV" not in dues_msgs[0]["body_zh"]
        assert "+6421" not in dues_msgs[0]["body_zh"]

        # 6. 标记已收 → 转正成功
        paid = client.post(
            f"/api/finance/ledger/{ledger_id}/mark-paid",
            headers=auth(world["finance"]),
        )
        assert paid.status_code == 200
        assert paid.json()["is_paid"] is True

        promote_ok = client.post(
            f"/api/members/{mid}/promote", headers=auth(world["super"])
        )
        assert promote_ok.status_code == 200
        assert promote_ok.json()["promoted"] is True
        assert promote_ok.json()["level"] == "formal"

        # 7. 发布活动 + 会员报名 → 收到报名成功消息
        start = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        aid = client.post(
            "/api/activities",
            json={
                "title": "E2E 周末下场",
                "activity_type": "weekly_round",
                "branch_id": world["branch_a"].id,
                "start_at": start,
            },
            headers=auth(world["super"]),
        ).json()["id"]
        client.post(f"/api/activities/{aid}/publish", headers=auth(world["super"]))

        reg = client.post(
            f"/api/activities/{aid}/register", json={}, headers=_token(uid)
        )
        assert reg.status_code == 200, reg.text

        inbox2 = client.get("/api/messages/me", headers=_token(uid)).json()
        assert any(m["message_type"] == "activity_registered" for m in inbox2)

        # 8. 账单接口返回本人两条以上收入流水
        bills = client.get("/api/finance/me/bills", headers=_token(uid))
        assert bills.status_code == 200
        assert all(b["member_id"] == mid for b in bills.json())
