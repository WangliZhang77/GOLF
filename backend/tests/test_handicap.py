from app.core.security import create_access_token
from tests.conftest import auth


def _create_member(client, world, username, handicap=None, branch=None, **overrides):
    payload = {
        "chinese_name": "差点会员",
        "branch_id": (branch or world["branch_a"]).id,
        "account_username": username,
        "account_password": "pw123456",
    }
    if handicap is not None:
        payload["handicap"] = handicap
    payload.update(overrides)
    resp = client.post("/api/members", json=payload, headers=auth(world["super"]))
    assert resp.status_code == 201, resp.text
    return resp.json()


def _token(uid: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(uid)}"}


class TestMyHandicap:
    def test_member_gets_own_dashboard(self, client, world):
        m = _create_member(client, world, handicap="18.0", username="hcme1")
        resp = client.get("/api/handicap/me", headers=_token(m["user_id"]))
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["current_handicap"] == "18.0"
        assert body["trend"] == "stable"
        assert body["history"] == []

    def test_no_member_profile_404(self, client, world):
        resp = client.get("/api/handicap/me", headers=auth(world["member"]))
        assert resp.status_code == 404


class TestAdjustHandicap:
    def test_manage_role_can_adjust_and_writes_history(self, client, world):
        m = _create_member(client, world, handicap="18.0", username="hcadj1")
        resp = client.patch(
            f"/api/handicap/members/{m['id']}",
            json={"new_handicap": "15.0", "remark": "根据近期成绩下调"},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["current_handicap"] == "15.0"
        assert len(body["history"]) == 1
        assert body["history"][0]["old_handicap"] == "18.0"
        assert body["history"][0]["new_handicap"] == "15.0"
        assert body["history"][0]["source"] == "manual"
        assert body["history"][0]["remark"] == "根据近期成绩下调"

        member_check = client.get(f"/api/members/{m['id']}", headers=auth(world["super"]))
        assert member_check.json()["handicap"] == "15.0"

    def test_non_manage_role_cannot_adjust(self, client, world):
        m = _create_member(client, world, handicap="18.0", username="hcadj2")
        resp = client.patch(
            f"/api/handicap/members/{m['id']}",
            json={"new_handicap": "15.0"},
            headers=auth(world["captain"]),
        )
        assert resp.status_code == 403

    def test_council_admin_scoped_to_own_branch(self, client, world):
        m = _create_member(client, world, handicap="18.0", branch=world["branch_b"], username="hcadj3")
        resp = client.patch(
            f"/api/handicap/members/{m['id']}",
            json={"new_handicap": "15.0"},
            headers=auth(world["council_a"]),
        )
        assert resp.status_code == 403

        ok = client.patch(
            f"/api/handicap/members/{m['id']}",
            json={"new_handicap": "15.0"},
            headers=auth(world["council_b"]),
        )
        assert ok.status_code == 200, ok.text

    def test_admin_member_update_no_longer_accepts_handicap(self, client, world):
        m = _create_member(client, world, handicap="18.0", username="hcadj4")
        resp = client.put(
            f"/api/members/{m['id']}",
            json={"handicap": "99.9", "golf_age": 3},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["handicap"] == "18.0"
        assert resp.json()["golf_age"] == 3

        history = client.get(f"/api/handicap/members/{m['id']}", headers=auth(world["super"]))
        assert history.json()["history"] == []


class TestTrend:
    def test_trend_stable_when_unchanged(self, client, world):
        m = _create_member(client, world, handicap="10.0", username="hctrend1")
        client.patch(
            f"/api/handicap/members/{m['id']}",
            json={"new_handicap": "10.0"},
            headers=auth(world["super"]),
        )
        resp = client.get(f"/api/handicap/members/{m['id']}", headers=auth(world["super"]))
        assert resp.json()["trend"] == "stable"

    def test_trend_declining_after_lower_adjustment(self, client, world):
        m = _create_member(client, world, handicap="18.0", username="hctrend2")
        client.patch(
            f"/api/handicap/members/{m['id']}",
            json={"new_handicap": "15.0"},
            headers=auth(world["super"]),
        )
        resp = client.get(f"/api/handicap/members/{m['id']}", headers=auth(world["super"]))
        assert resp.json()["trend"] == "declining"

    def test_trend_rising_after_higher_adjustment(self, client, world):
        m = _create_member(client, world, handicap="10.0", username="hctrend3")
        client.patch(
            f"/api/handicap/members/{m['id']}",
            json={"new_handicap": "12.5"},
            headers=auth(world["super"]),
        )
        resp = client.get(f"/api/handicap/members/{m['id']}", headers=auth(world["super"]))
        assert resp.json()["trend"] == "rising"
