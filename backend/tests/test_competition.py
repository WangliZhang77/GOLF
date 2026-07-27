from datetime import datetime, timedelta, timezone

from app.core.security import create_access_token
from tests.conftest import auth


def _create_open_competition(client, world, **overrides):
    start = datetime.now(timezone.utc) + timedelta(days=21)
    payload = {
        "name": "公开赛",
        "competition_type": "official",
        "branch_id": world["branch_a"].id,
        "start_time": start.isoformat(),
        "max_players": 10,
    }
    payload.update(overrides)
    r = client.post("/api/competitions", json=payload, headers=auth(world["super"]))
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    client.post(f"/api/competitions/{cid}/publish", headers=auth(world["super"]))
    return cid


def _member_with_profile(client, world, username="comp_member", handicap=None, **overrides):
    payload = {
        "chinese_name": "赛事会员",
        "branch_id": world["branch_a"].id,
        "account_username": username,
        "account_password": "pw123456",
    }
    if handicap is not None:
        payload["handicap"] = handicap
    payload.update(overrides)
    resp = client.post("/api/members", json=payload, headers=auth(world["super"]))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body, body["user_id"]


def _token(uid: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(uid)}"}


class TestCompetitionCrud:
    def test_create_and_publish(self, client, world):
        cid = _create_open_competition(client, world)
        resp = client.get(f"/api/competitions/{cid}", headers=auth(world["super"]))
        assert resp.status_code == 200
        assert resp.json()["status"] == "open"

    def test_council_admin_cannot_create_hq_wide_competition(self, client, world):
        start = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        resp = client.post(
            "/api/competitions",
            json={
                "name": "总会赛事",
                "competition_type": "official",
                "branch_id": None,
                "start_time": start,
            },
            headers=auth(world["council_a"]),
        )
        assert resp.status_code == 403

    def test_member_cannot_create(self, client, world):
        start = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        resp = client.post(
            "/api/competitions",
            json={
                "name": "非法赛事",
                "competition_type": "official",
                "branch_id": world["branch_a"].id,
                "start_time": start,
            },
            headers=auth(world["member"]),
        )
        assert resp.status_code == 403


class TestCourseCrud:
    def test_create_and_list_course(self, client, world):
        resp = client.post(
            "/api/courses",
            json={"name_zh": "测试球场"},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 201, resp.text
        listed = client.get("/api/courses", headers=auth(world["member"])).json()
        assert any(c["name_zh"] == "测试球场" for c in listed)

    def test_member_can_list_but_not_create(self, client, world):
        resp = client.post(
            "/api/courses",
            json={"name_zh": "非法球场"},
            headers=auth(world["member"]),
        )
        assert resp.status_code == 403
        listed = client.get("/api/courses", headers=auth(world["member"]))
        assert listed.status_code == 200

    def test_course_extended_fields_round_trip(self, client, world):
        resp = client.post(
            "/api/courses",
            json={
                "name_zh": "详细球场",
                "city": "Auckland",
                "holes": 18,
                "par": 72,
                "rating": "72.3",
                "slope": 130,
            },
            headers=auth(world["super"]),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["city"] == "Auckland"
        assert body["par"] == 72
        assert body["rating"] == "72.3"
        assert body["slope"] == 130

    def test_course_slope_out_of_range_rejected(self, client, world):
        resp = client.post(
            "/api/courses",
            json={"name_zh": "超范围球场", "slope": 200},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 422


class TestRegistrationEligibility:
    def test_register_success_within_handicap_limit(self, client, world):
        cid = _create_open_competition(client, world, max_handicap="24.0")
        _, uid = _member_with_profile(client, world, "elig1", handicap="18.0")
        resp = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["approval_status"] == "pending"

    def test_register_fails_handicap_too_high(self, client, world):
        cid = _create_open_competition(client, world, max_handicap="20.0")
        _, uid = _member_with_profile(client, world, "elig2", handicap="25.0")
        resp = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        )
        assert resp.status_code == 403

    def test_register_fails_handicap_missing_but_required(self, client, world):
        cid = _create_open_competition(client, world, max_handicap="20.0")
        _, uid = _member_with_profile(client, world, "elig3")
        resp = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        )
        assert resp.status_code == 403
        assert "差点信息缺失" in resp.json()["detail"]

    def test_register_succeeds_when_no_handicap_restriction(self, client, world):
        cid = _create_open_competition(client, world)
        _, uid = _member_with_profile(client, world, "elig4")
        resp = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        )
        assert resp.status_code == 201, resp.text

    def test_register_fails_outstanding_dues(self, client, world):
        cid = _create_open_competition(client, world)
        body, uid = _member_with_profile(client, world, "elig5")
        client.post(
            "/api/finance/ledger",
            json={
                "direction": "income",
                "category": "annual_dues",
                "amount": "120.00",
                "title": "欠费测试",
                "member_id": body["id"],
                "branch_id": world["branch_a"].id,
                "is_paid": False,
            },
            headers=auth(world["finance"]),
        )
        resp = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        )
        assert resp.status_code == 403

    def test_register_fails_blacklisted_member(self, client, world):
        cid = _create_open_competition(client, world)
        body, uid = _member_with_profile(client, world, "elig6")
        client.post(
            f"/api/members/{body['id']}/blacklist", headers=auth(world["super"])
        )
        resp = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        )
        assert resp.status_code == 403

    def test_register_fails_inactive_member(self, client, world, db):
        cid = _create_open_competition(client, world)
        body, uid = _member_with_profile(client, world, "elig7")

        from app.models.member import Member, MemberStatus

        m = db.query(Member).filter(Member.id == body["id"]).first()
        m.status = MemberStatus.sleeping
        db.commit()

        resp = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        )
        assert resp.status_code == 403

    def test_register_fails_capacity_full(self, client, world):
        cid = _create_open_competition(client, world, max_players=1)
        _, uid1 = _member_with_profile(client, world, "cap1")
        _, uid2 = _member_with_profile(client, world, "cap2")
        r1 = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid1)
        )
        assert r1.status_code == 201, r1.text
        r2 = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid2)
        )
        assert r2.status_code == 409

    def test_register_fails_duplicate(self, client, world):
        cid = _create_open_competition(client, world)
        _, uid = _member_with_profile(client, world, "dup1")
        r1 = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        )
        assert r1.status_code == 201, r1.text
        r2 = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        )
        assert r2.status_code == 409

    def test_register_fails_after_deadline(self, client, world):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        cid = _create_open_competition(client, world, registration_deadline=past)
        _, uid = _member_with_profile(client, world, "dl1")
        resp = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        )
        assert resp.status_code == 409

    def test_register_fails_when_not_open(self, client, world):
        start = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
        created = client.post(
            "/api/competitions",
            json={
                "name": "草稿赛事",
                "competition_type": "official",
                "branch_id": world["branch_a"].id,
                "start_time": start,
            },
            headers=auth(world["super"]),
        )
        cid = created.json()["id"]
        _, uid = _member_with_profile(client, world, "draft1")
        resp = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        )
        assert resp.status_code == 409


class TestApproval:
    def test_manage_role_can_approve(self, client, world):
        cid = _create_open_competition(client, world)
        _, uid = _member_with_profile(client, world, "app1")
        reg = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        ).json()
        resp = client.post(
            f"/api/competitions/{cid}/registrations/{reg['id']}/approve",
            json={"approve": True},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200
        assert resp.json()["approval_status"] == "approved"

    def test_manage_role_can_reject_with_remark(self, client, world):
        cid = _create_open_competition(client, world)
        _, uid = _member_with_profile(client, world, "app2")
        reg = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        ).json()
        resp = client.post(
            f"/api/competitions/{cid}/registrations/{reg['id']}/approve",
            json={"approve": False, "remark": "资格不符"},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200
        assert resp.json()["approval_status"] == "rejected"
        assert resp.json()["remark"] == "资格不符"

    def test_non_manage_role_cannot_approve(self, client, world):
        cid = _create_open_competition(client, world)
        _, uid = _member_with_profile(client, world, "app3")
        reg = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        ).json()
        resp = client.post(
            f"/api/competitions/{cid}/registrations/{reg['id']}/approve",
            json={"approve": True},
            headers=auth(world["captain"]),
        )
        assert resp.status_code == 403

    def test_event_director_can_approve_any_branch(self, client, world):
        cid = _create_open_competition(client, world, branch_id=world["branch_b"].id)
        _, uid = _member_with_profile(
            client, world, "app4", branch_id=world["branch_b"].id
        )
        reg = client.post(
            f"/api/competitions/{cid}/register", json={}, headers=_token(uid)
        ).json()
        resp = client.post(
            f"/api/competitions/{cid}/registrations/{reg['id']}/approve",
            json={"approve": True},
            headers=auth(world["event_director"]),
        )
        assert resp.status_code == 200
