from datetime import datetime, timedelta, timezone

from app.core.security import create_access_token
from tests.conftest import auth


def _create_open_competition(client, world, **overrides):
    start = datetime.now(timezone.utc) + timedelta(days=21)
    payload = {
        "name": "分组测试赛",
        "competition_type": "official",
        "branch_id": world["branch_a"].id,
        "start_time": start.isoformat(),
        "max_players": 40,
    }
    payload.update(overrides)
    r = client.post("/api/competitions", json=payload, headers=auth(world["super"]))
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    client.post(f"/api/competitions/{cid}/publish", headers=auth(world["super"]))
    return cid


def _member_with_profile(client, world, username, handicap=None, **overrides):
    payload = {
        "chinese_name": "分组会员",
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


def _register_and_approve(client, world, cid, username, handicap=None):
    body, uid = _member_with_profile(client, world, username, handicap=handicap)
    r = client.post(f"/api/competitions/{cid}/register", json={}, headers=_token(uid))
    assert r.status_code == 201, r.text
    reg_id = r.json()["id"]
    approve = client.post(
        f"/api/competitions/{cid}/registrations/{reg_id}/approve",
        json={"approve": True},
        headers=auth(world["super"]),
    )
    assert approve.status_code == 200, approve.text
    return body, uid


class TestGenerateGroups:
    def test_generate_groups_basic(self, client, world):
        cid = _create_open_competition(client, world)
        for i in range(8):
            _register_and_approve(client, world, cid, f"grp{i}", handicap=f"{10 + i}.0")

        resp = client.post(
            f"/api/competitions/{cid}/groups/generate",
            json={"group_size": 4},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200, resp.text
        groups = resp.json()
        assert len(groups) == 2
        assert sum(len(g["players"]) for g in groups) == 8

    def test_generate_requires_manage_role(self, client, world):
        cid = _create_open_competition(client, world)
        resp = client.post(
            f"/api/competitions/{cid}/groups/generate",
            json={},
            headers=auth(world["member"]),
        )
        assert resp.status_code == 403

    def test_regenerate_needs_force(self, client, world):
        cid = _create_open_competition(client, world)
        for i in range(4):
            _register_and_approve(client, world, cid, f"rg{i}", handicap="15.0")
        client.post(
            f"/api/competitions/{cid}/groups/generate",
            json={},
            headers=auth(world["super"]),
        )
        again = client.post(
            f"/api/competitions/{cid}/groups/generate",
            json={},
            headers=auth(world["super"]),
        )
        assert again.status_code == 409

        forced = client.post(
            f"/api/competitions/{cid}/groups/generate",
            json={"force": True},
            headers=auth(world["super"]),
        )
        assert forced.status_code == 200, forced.text

    def test_list_groups_any_authenticated_user(self, client, world):
        cid = _create_open_competition(client, world)
        for i in range(4):
            _register_and_approve(client, world, cid, f"lg{i}", handicap="12.0")
        client.post(
            f"/api/competitions/{cid}/groups/generate",
            json={},
            headers=auth(world["super"]),
        )
        resp = client.get(f"/api/competitions/{cid}/groups", headers=auth(world["member"]))
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestMoveAndSwap:
    def test_move_player_to_another_group(self, client, world):
        cid = _create_open_competition(client, world)
        for i in range(8):
            _register_and_approve(client, world, cid, f"mv{i}", handicap=f"{10 + i}.0")
        gen = client.post(
            f"/api/competitions/{cid}/groups/generate",
            json={"group_size": 4},
            headers=auth(world["super"]),
        ).json()
        group_a, group_b = gen[0], gen[1]
        player = group_a["players"][0]

        resp = client.post(
            f"/api/competitions/{cid}/groups/players/{player['id']}/move",
            json={"target_group_id": group_b["id"]},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["id"] == group_b["id"]
        member_ids = [p["member_id"] for p in resp.json()["players"]]
        assert player["member_id"] in member_ids

    def test_swap_players(self, client, world):
        cid = _create_open_competition(client, world)
        for i in range(8):
            _register_and_approve(client, world, cid, f"sw{i}", handicap=f"{10 + i}.0")
        gen = client.post(
            f"/api/competitions/{cid}/groups/generate",
            json={"group_size": 4},
            headers=auth(world["super"]),
        ).json()
        player_a = gen[0]["players"][0]
        player_b = gen[1]["players"][0]

        resp = client.post(
            f"/api/competitions/{cid}/groups/swap",
            json={"player_id_a": player_a["id"], "player_id_b": player_b["id"]},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200, resp.text


class TestMyGroup:
    def test_member_can_view_own_group(self, client, world):
        cid = _create_open_competition(client, world)
        body, uid = _register_and_approve(client, world, cid, "myg1", handicap="14.0")
        for i in range(3):
            _register_and_approve(client, world, cid, f"myg_other{i}", handicap=f"{15 + i}.0")
        client.post(
            f"/api/competitions/{cid}/groups/generate",
            json={"group_size": 4},
            headers=auth(world["super"]),
        )
        resp = client.get(f"/api/competitions/{cid}/groups/my-group", headers=_token(uid))
        assert resp.status_code == 200, resp.text
        member_ids = [p["member_id"] for p in resp.json()["players"]]
        assert body["id"] in member_ids

    def test_ungrouped_member_gets_404(self, client, world):
        cid = _create_open_competition(client, world)
        _, uid = _member_with_profile(client, world, "myg_none")
        resp = client.get(f"/api/competitions/{cid}/groups/my-group", headers=_token(uid))
        assert resp.status_code == 404


class TestStartCompetition:
    def test_start_blocked_without_groups(self, client, world):
        cid = _create_open_competition(client, world)
        resp = client.post(f"/api/competitions/{cid}/start", headers=auth(world["super"]))
        assert resp.status_code == 409

    def test_start_blocked_with_unassigned_member(self, client, world):
        cid = _create_open_competition(client, world)
        for i in range(4):
            _register_and_approve(client, world, cid, f"st{i}", handicap="12.0")
        client.post(
            f"/api/competitions/{cid}/groups/generate",
            json={},
            headers=auth(world["super"]),
        )
        # 分组后再新批一个报名，制造未分组会员
        _register_and_approve(client, world, cid, "st_extra", handicap="20.0")
        resp = client.post(f"/api/competitions/{cid}/start", headers=auth(world["super"]))
        assert resp.status_code == 409

    def test_start_succeeds_when_fully_grouped(self, client, world):
        cid = _create_open_competition(client, world)
        for i in range(4):
            _register_and_approve(client, world, cid, f"ok{i}", handicap="12.0")
        client.post(
            f"/api/competitions/{cid}/groups/generate",
            json={},
            headers=auth(world["super"]),
        )
        resp = client.post(f"/api/competitions/{cid}/start", headers=auth(world["super"]))
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "playing"

        detail = client.get(f"/api/competitions/{cid}", headers=auth(world["super"]))
        assert detail.json()["status"] == "playing"
