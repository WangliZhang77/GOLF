from datetime import datetime, timedelta, timezone

from app.core.security import create_access_token
from tests.conftest import auth


def _create_published_activity(client, world, **overrides):
    start = datetime.now(timezone.utc) + timedelta(days=7)
    payload = {
        "title": "周末下场",
        "activity_type": "weekly_round",
        "branch_id": world["branch_a"].id,
        "start_at": start.isoformat(),
        "max_participants": 10,
        "max_family_slots": 2,
        "family_allowed": True,
    }
    payload.update(overrides)
    r = client.post("/api/activities", json=payload, headers=auth(world["super"]))
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    client.post(f"/api/activities/{aid}/publish", headers=auth(world["super"]))
    return aid


def _member_with_profile(client, world, username="act_member"):
    resp = client.post(
        "/api/members",
        json={
            "chinese_name": "活动会员",
            "branch_id": world["branch_a"].id,
            "account_username": username,
            "account_password": "pw123456",
        },
        headers=auth(world["super"]),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body, body["user_id"]


def _token(uid: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(uid)}"}


class TestActivityCrud:
    def test_create_and_publish(self, client, world):
        aid = _create_published_activity(client, world)
        resp = client.get(f"/api/activities/{aid}", headers=auth(world["super"]))
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

    def test_member_cannot_create(self, client, world):
        start = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        resp = client.post(
            "/api/activities",
            json={
                "title": "非法",
                "activity_type": "weekly_round",
                "branch_id": world["branch_a"].id,
                "start_at": start,
            },
            headers=auth(world["member"]),
        )
        assert resp.status_code == 403


class TestRegistration:
    def test_register_with_family(self, client, world):
        aid = _create_published_activity(client, world)
        _, uid = _member_with_profile(client, world, "fam_user")
        resp = client.post(
            f"/api/activities/{aid}/register",
            json={
                "family_companions": [
                    {"name": "家属甲", "relation": "配偶"},
                    {"name": "家属乙", "relation": "子女"},
                ]
            },
            headers=_token(uid),
        )
        assert resp.status_code == 200, resp.text
        rows = resp.json()
        assert len(rows) == 3
        assert sum(1 for r in rows if r["registrant_type"] == "family") == 2

        stats = client.get(
            f"/api/activities/{aid}/attendance-stats", headers=auth(world["super"])
        ).json()
        assert stats["member_registered"] == 1
        assert stats["family_registered"] == 2

    def test_capacity_full(self, client, world):
        aid = _create_published_activity(client, world, max_participants=1)
        _, uid1 = _member_with_profile(client, world, "cap1")
        _, uid2 = _member_with_profile(client, world, "cap2")
        client.post(f"/api/activities/{aid}/register", json={}, headers=_token(uid1))
        r2 = client.post(
            f"/api/activities/{aid}/register", json={}, headers=_token(uid2)
        )
        assert r2.status_code == 409

    def test_blacklist_cannot_register(self, client, world):
        aid = _create_published_activity(client, world)
        body, uid = _member_with_profile(client, world, "blk_user")
        client.post(
            f"/api/members/{body['id']}/blacklist", headers=auth(world["super"])
        )
        resp = client.post(
            f"/api/activities/{aid}/register", json={}, headers=_token(uid)
        )
        assert resp.status_code == 403


class TestCheckin:
    def test_checkin_flow(self, client, world, db):
        aid = _create_published_activity(client, world)
        created, uid = _member_with_profile(client, world, "chk_user")
        client.post(f"/api/activities/{aid}/register", json={}, headers=_token(uid))

        act = client.get(f"/api/activities/{aid}", headers=auth(world["super"])).json()
        chk = client.post(
            f"/api/activities/{aid}/checkin",
            json={"token": act["checkin_token"]},
            headers=_token(uid),
        )
        assert chk.status_code == 200, chk.text
        assert chk.json()[0]["status"] == "checked_in"

        from app.models.member import Member

        db.expire_all()
        m = db.query(Member).filter(Member.id == created["id"]).first()
        assert m.last_active_at is not None

    def test_invalid_token(self, client, world):
        aid = _create_published_activity(client, world)
        _, uid = _member_with_profile(client, world, "bad_chk")
        client.post(f"/api/activities/{aid}/register", json={}, headers=_token(uid))
        resp = client.post(
            f"/api/activities/{aid}/checkin",
            json={"token": "wrong"},
            headers=_token(uid),
        )
        assert resp.status_code == 403


class TestAbsent:
    def test_mark_absent(self, client, world):
        aid = _create_published_activity(client, world)
        _, uid = _member_with_profile(client, world, "abs_user")
        regs = client.post(
            f"/api/activities/{aid}/register", json={}, headers=_token(uid)
        ).json()
        resp = client.post(
            f"/api/activities/{aid}/registrations/{regs[0]['id']}/mark-absent",
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "absent"
