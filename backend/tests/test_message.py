from app.core.security import create_access_token
from tests.conftest import auth


def _token(uid: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(uid)}"}


def _create_member(client, world, username="msg_user"):
    resp = client.post(
        "/api/members",
        json={
            "chinese_name": "消息测试",
            "branch_id": world["branch_a"].id,
            "passport_no": "MSG-PRIV-001",
            "local_phone": "+64218888888",
            "account_username": username,
            "account_password": "pw123456",
        },
        headers=auth(world["super"]),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _ledger_payload(member_id: int):
    return {
        "direction": "income",
        "category": "annual_dues",
        "amount": "120.00",
        "title": "2026 年度会费",
        "member_id": member_id,
        "is_paid": False,
    }


class TestRegistrationNotification:
    def test_register_sends_activity_message(self, client, world):
        from datetime import datetime, timedelta, timezone

        start = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        aid = client.post(
            "/api/activities",
            json={
                "title": "消息测试活动",
                "activity_type": "weekly_round",
                "branch_id": world["branch_a"].id,
                "start_at": start,
            },
            headers=auth(world["super"]),
        ).json()["id"]
        client.post(f"/api/activities/{aid}/publish", headers=auth(world["super"]))

        member = _create_member(client, world, "reg_msg_user")
        uid = member["user_id"]
        client.post(
            f"/api/activities/{aid}/register",
            json={},
            headers=_token(uid),
        )

        msgs = client.get("/api/messages/me", headers=_token(uid))
        assert msgs.status_code == 200
        assert len(msgs.json()) >= 1
        m = msgs.json()[0]
        assert m["message_type"] == "activity_registered"
        assert "消息测试活动" in m["body_zh"]
        assert "passport" not in m["body_zh"].lower()
        assert "+6421" not in m["body_zh"]
        assert m["title_zh"] and m["title_en"]
        assert m["body_zh"] and m["body_en"]


class TestDuesReminder:
    def test_finance_can_send_dues_reminder(self, client, world):
        member = _create_member(client, world, "dues_user")
        mid = member["id"]
        uid = member["user_id"]
        client.post(
            "/api/finance/ledger",
            json=_ledger_payload(mid),
            headers=auth(world["finance"]),
        )
        resp = client.post(
            "/api/messages/dues-reminder",
            json={"member_id": mid},
            headers=auth(world["finance"]),
        )
        assert resp.status_code == 200
        assert resp.json()["sent_count"] >= 1

        msgs = client.get("/api/messages/me", headers=_token(uid))
        assert any(m["message_type"] == "dues_reminder" for m in msgs.json())
        body = next(m for m in msgs.json() if m["message_type"] == "dues_reminder")
        assert "MSG-PRIV" not in body["body_zh"]
        assert "+6421" not in body["body_zh"]

    def test_member_cannot_send_dues_reminder(self, client, world):
        resp = client.post(
            "/api/messages/dues-reminder",
            json={"member_id": 1},
            headers=auth(world["member"]),
        )
        assert resp.status_code == 403

    def test_batch_dues_only_outstanding(self, client, world):
        owing = _create_member(client, world, "owing_user")
        paid = _create_member(client, world, "paid_user")
        client.post(
            "/api/finance/ledger",
            json=_ledger_payload(owing["id"]),
            headers=auth(world["finance"]),
        )
        client.post(
            "/api/finance/ledger",
            json={**_ledger_payload(paid["id"]), "is_paid": True},
            headers=auth(world["finance"]),
        )
        resp = client.post(
            "/api/messages/dues-reminder",
            json={"all_outstanding": True},
            headers=auth(world["finance"]),
        )
        assert resp.status_code == 200
        assert resp.json()["sent_count"] >= 1

        owing_msgs = client.get("/api/messages/me", headers=_token(owing["user_id"])).json()
        paid_msgs = client.get("/api/messages/me", headers=_token(paid["user_id"])).json()
        assert any(m["message_type"] == "dues_reminder" for m in owing_msgs)
        assert not any(m["message_type"] == "dues_reminder" for m in paid_msgs)


class TestInbox:
    def test_me_only_own_messages(self, client, world):
        a = _create_member(client, world, "inbox_a")
        b = _create_member(client, world, "inbox_b")
        client.post(
            "/api/finance/ledger",
            json=_ledger_payload(a["id"]),
            headers=auth(world["finance"]),
        )
        client.post(
            "/api/messages/dues-reminder",
            json={"member_id": a["id"]},
            headers=auth(world["finance"]),
        )
        a_msgs = client.get("/api/messages/me", headers=_token(a["user_id"]))
        b_msgs = client.get("/api/messages/me", headers=_token(b["user_id"]))
        assert len(a_msgs.json()) >= 1
        assert b_msgs.json() == []

    def test_read_and_unread_count(self, client, world):
        member = _create_member(client, world, "read_user")
        mid = member["id"]
        uid = member["user_id"]
        client.post(
            "/api/finance/ledger",
            json=_ledger_payload(mid),
            headers=auth(world["finance"]),
        )
        client.post(
            "/api/messages/dues-reminder",
            json={"member_id": mid},
            headers=auth(world["finance"]),
        )
        unread = client.get("/api/messages/me/unread-count", headers=_token(uid))
        assert unread.json()["count"] >= 1

        msg_id = client.get("/api/messages/me", headers=_token(uid)).json()[0]["id"]
        read = client.post(f"/api/messages/me/{msg_id}/read", headers=_token(uid))
        assert read.status_code == 200
        assert read.json()["is_read"] is True

        unread2 = client.get("/api/messages/me/unread-count", headers=_token(uid))
        assert unread2.json()["count"] == unread.json()["count"] - 1

        client.post(
            "/api/finance/ledger",
            json={**_ledger_payload(mid), "title": "第二笔"},
            headers=auth(world["finance"]),
        )
        client.post(
            "/api/messages/dues-reminder",
            json={"member_id": mid},
            headers=auth(world["finance"]),
        )
        client.post("/api/messages/me/read-all", headers=_token(uid))
        assert client.get("/api/messages/me/unread-count", headers=_token(uid)).json()["count"] == 0
