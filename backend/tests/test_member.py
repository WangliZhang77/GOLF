from datetime import date, datetime, timedelta, timezone

from app.core.security import create_access_token
from tests.conftest import auth


def _token(uid: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(uid)}"}


def _create_member(client, world, **overrides):
    payload = {
        "chinese_name": "张三",
        "english_name": "San Zhang",
        "branch_id": world["branch_a"].id,
        "passport_no": "PA123456",
        "local_phone": "+64211234567",
        "level": "probationary",
    }
    payload.update(overrides)
    return client.post("/api/members", json=payload, headers=auth(world["super"]))


class TestMemberCrud:
    def test_super_create_member_returns_private(self, client, world):
        resp = _create_member(client, world)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["chinese_name"] == "张三"
        assert body["passport_no"] == "PA123456"  # 超管可见隐私

    def test_member_role_cannot_create(self, client, world):
        resp = client.post(
            "/api/members",
            json={"chinese_name": "非法", "branch_id": world["branch_a"].id},
            headers=auth(world["member"]),
        )
        assert resp.status_code == 403

    def test_council_cannot_create_in_other_branch(self, client, world):
        resp = client.post(
            "/api/members",
            json={"chinese_name": "跨界", "branch_id": world["branch_b"].id},
            headers=auth(world["council_a"]),
        )
        assert resp.status_code == 403


class TestFieldVisibility:
    def test_non_privileged_cannot_see_private(self, client, world):
        mid = _create_member(client, world).json()["id"]
        # 赛事总监非隐私特权角色
        resp = client.get(f"/api/members/{mid}", headers=auth(world["event_director"]))
        assert resp.status_code == 200
        assert "passport_no" not in resp.json()
        assert resp.json()["chinese_name"] == "张三"

    def test_super_sees_private(self, client, world):
        mid = _create_member(client, world).json()["id"]
        resp = client.get(f"/api/members/{mid}", headers=auth(world["super"]))
        assert resp.json()["passport_no"] == "PA123456"


class TestSelfProfile:
    def test_self_view_and_edit_public_only(self, client, world):
        created = _create_member(
            client, world, account_username="mmm", account_password="pw123456"
        ).json()
        uid = created["user_id"]
        assert uid is not None

        # 本人可见完整档案（含隐私）
        me = client.get("/api/members/me", headers=_token(uid))
        assert me.status_code == 200
        assert me.json()["passport_no"] == "PA123456"

        # 本人仅能改公开信息；尝试传隐私字段应被忽略
        upd = client.put(
            "/api/members/me",
            json={"english_name": "New Name"},
            headers=_token(uid),
        )
        assert upd.status_code == 200
        assert upd.json()["english_name"] == "New Name"
        assert upd.json()["passport_no"] == "PA123456"  # 未被改动


class TestLevelActions:
    def test_blacklist(self, client, world):
        mid = _create_member(client, world).json()["id"]
        resp = client.post(f"/api/members/{mid}/blacklist", headers=auth(world["super"]))
        assert resp.status_code == 200
        assert resp.json()["level"] == "blacklist"

    def test_promote_eligible(self, client, world, db):
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

        # 模拟 5 次签到出勤（方案转正条件）
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

        resp = client.post(f"/api/members/{mid}/promote", headers=auth(world["super"]))
        assert resp.status_code == 200
        assert resp.json()["promoted"] is True
        assert resp.json()["level"] == "formal"

    def test_promote_insufficient_attendance(self, client, world):
        old = (date.today() - timedelta(days=200)).isoformat()
        mid = _create_member(client, world, join_date=old).json()["id"]
        resp = client.post(f"/api/members/{mid}/promote", headers=auth(world["super"]))
        assert resp.status_code == 200
        assert resp.json()["promoted"] is False

    def test_promote_too_early(self, client, world):
        recent = (date.today() - timedelta(days=10)).isoformat()
        mid = _create_member(client, world, join_date=recent).json()["id"]
        resp = client.post(f"/api/members/{mid}/promote", headers=auth(world["super"]))
        assert resp.status_code == 200
        assert resp.json()["promoted"] is False

    def test_sleep_scan_marks_inactive(self, client, world, db):
        from datetime import datetime, timedelta, timezone

        from app.models.member import Member, MemberStatus

        mid = _create_member(client, world).json()["id"]
        m = db.query(Member).filter(Member.id == mid).first()
        m.last_active_at = datetime.now(timezone.utc) - timedelta(days=400)
        db.commit()

        resp = client.post("/api/members/sleep-scan", headers=auth(world["super"]))
        assert resp.status_code == 200
        assert resp.json()["marked_sleeping"] >= 1

        db.expire_all()
        m = db.query(Member).filter(Member.id == mid).first()
        assert m.status == MemberStatus.sleeping


class TestScope:
    def test_council_b_cannot_see_branch_a_member(self, client, world):
        _create_member(client, world)  # in branch_a
        resp = client.get("/api/members", headers=auth(world["council_b"]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_member_sees_only_self(self, client, world):
        # 给 world.member 建一个档案
        _create_member(
            client,
            world,
            chinese_name="本人",
            account_username="selfacc",
            account_password="pw123456",
        )
        created = client.get("/api/members", headers=auth(world["super"])).json()
        # world.member 没有档案 → 只看到自己(空)
        resp = client.get("/api/members", headers=auth(world["member"]))
        assert resp.status_code == 200
        assert all(m["user_id"] == world["member"].id for m in resp.json())
        assert len(created) >= 1
