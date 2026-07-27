from datetime import datetime, timedelta, timezone

from app.core.security import create_access_token
from tests.conftest import auth


def _create_open_competition(client, world, **overrides):
    start = datetime.now(timezone.utc) + timedelta(days=21)
    payload = {
        "name": "排名测试赛",
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
        "chinese_name": "排名会员",
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


def _register_and_approve(client, world, cid, username, handicap=None, **overrides):
    body, uid = _member_with_profile(client, world, username, handicap=handicap, **overrides)
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


def _get_card_for_member(client, cid, uid) -> dict:
    r = client.get(f"/api/competitions/{cid}/scorecards/mine", headers=_token(uid))
    assert r.status_code == 200, r.text
    return r.json()


def _fill_and_submit(client, cid, uid, card_id, extra_first_hole=0):
    for h in range(1, 19):
        strokes = 4 + (extra_first_hole if h == 1 else 0)
        r = client.patch(
            f"/api/competitions/{cid}/scorecards/{card_id}/hole",
            json={"hole_number": h, "strokes": strokes},
            headers=_token(uid),
        )
        assert r.status_code == 200, r.text
    sub = client.post(f"/api/competitions/{cid}/scorecards/{card_id}/submit", headers=_token(uid))
    assert sub.status_code == 200, sub.text


def _setup_reviewed_competition(client, world, n_players=4, handicap="10.0", team_ids=None):
    """报名审核→分组→开赛→逐洞记分（第 i 位球员第1洞多打 i 杆，制造成绩差异）→提交→管理员通过→结束比赛。"""
    cid = _create_open_competition(client, world)
    players = []
    for i in range(n_players):
        overrides = {}
        if team_ids and team_ids[i] is not None:
            overrides["team_id"] = team_ids[i]
        body, uid = _register_and_approve(client, world, cid, f"rk{i}", handicap=handicap, **overrides)
        players.append((body, uid))

    client.post(
        f"/api/competitions/{cid}/groups/generate",
        json={"group_size": n_players},
        headers=auth(world["super"]),
    )
    start = client.post(f"/api/competitions/{cid}/start", headers=auth(world["super"]))
    assert start.status_code == 200, start.text

    for i, (body, uid) in enumerate(players):
        card = _get_card_for_member(client, cid, uid)
        _fill_and_submit(client, cid, uid, card["id"], extra_first_hole=i)
        approve = client.post(
            f"/api/competitions/{cid}/scorecards/{card['id']}/admin-review",
            json={"approve": True},
            headers=auth(world["super"]),
        )
        assert approve.status_code == 200, approve.text

    close = client.post(f"/api/competitions/{cid}/close-play", headers=auth(world["super"]))
    assert close.status_code == 200, close.text
    return cid, players


class TestPreview:
    def test_preview_requires_manage_role(self, client, world):
        cid, players = _setup_reviewed_competition(client, world, n_players=2)
        _, uid = players[0]
        resp = client.get(f"/api/competitions/{cid}/rankings/preview", headers=_token(uid))
        assert resp.status_code == 403

    def test_preview_orders_by_net_score_without_persisting(self, client, world):
        cid, players = _setup_reviewed_competition(client, world, n_players=3)
        resp = client.get(
            f"/api/competitions/{cid}/rankings/preview?scope=individual",
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200, resp.text
        rows = resp.json()
        assert len(rows) == 3
        # 第0位球员没有额外杆数，成绩最好，应排第一
        assert rows[0]["rank"] == 1
        assert rows[0]["member_id"] == players[0][0]["id"]
        assert rows[0]["award"] == "champion"

        persisted = client.get(f"/api/competitions/{cid}/rankings", headers=auth(world["super"]))
        assert persisted.json() == []


class TestPublish:
    def test_publish_blocked_before_review_status(self, client, world):
        cid = _create_open_competition(client, world)
        resp = client.post(f"/api/competitions/{cid}/rankings/publish", headers=auth(world["super"]))
        assert resp.status_code == 409

    def test_publish_blocked_with_unapproved_cards(self, client, world):
        cid = _create_open_competition(client, world)
        _, uid = _register_and_approve(client, world, cid, "rkpending", handicap="10.0")
        client.post(
            f"/api/competitions/{cid}/groups/generate", json={}, headers=auth(world["super"])
        )
        client.post(f"/api/competitions/{cid}/start", headers=auth(world["super"]))
        card = _get_card_for_member(client, cid, uid)
        _fill_and_submit(client, cid, uid, card["id"])
        # 不批准，直接尝试结束比赛应被拦（仍有未提交/未审核卡不影响 close-play，只看 draft）
        close = client.post(f"/api/competitions/{cid}/close-play", headers=auth(world["super"]))
        assert close.status_code == 200, close.text

        resp = client.post(f"/api/competitions/{cid}/rankings/publish", headers=auth(world["super"]))
        assert resp.status_code == 409

    def test_publish_success_sets_completed_and_creates_rankings(self, client, world):
        cid, players = _setup_reviewed_competition(client, world, n_players=4)
        resp = client.post(f"/api/competitions/{cid}/rankings/publish", headers=auth(world["super"]))
        assert resp.status_code == 200, resp.text
        rows = resp.json()
        individual = [r for r in rows if r["scope"] == "individual"]
        assert len(individual) == 4
        assert individual[0]["rank"] == 1
        assert individual[0]["member_id"] == players[0][0]["id"]

        comp = client.get(f"/api/competitions/{cid}", headers=auth(world["super"]))
        assert comp.json()["status"] == "completed"

    def test_republish_from_completed_replaces_rows(self, client, world):
        cid, players = _setup_reviewed_competition(client, world, n_players=2)
        first = client.post(f"/api/competitions/{cid}/rankings/publish", headers=auth(world["super"]))
        assert first.status_code == 200, first.text

        second = client.post(f"/api/competitions/{cid}/rankings/publish", headers=auth(world["super"]))
        assert second.status_code == 200, second.text

        listed = client.get(f"/api/competitions/{cid}/rankings?scope=individual", headers=auth(world["super"]))
        assert len(listed.json()) == 2


class TestListAndAward:
    def test_list_rankings_empty_before_publish(self, client, world):
        cid, players = _setup_reviewed_competition(client, world, n_players=2)
        resp = client.get(f"/api/competitions/{cid}/rankings", headers=auth(world["super"]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_any_authenticated_user_can_list_after_publish(self, client, world):
        cid, players = _setup_reviewed_competition(client, world, n_players=2)
        client.post(f"/api/competitions/{cid}/rankings/publish", headers=auth(world["super"]))
        _, uid = players[0]
        resp = client.get(f"/api/competitions/{cid}/rankings", headers=_token(uid))
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_patch_award(self, client, world):
        cid, players = _setup_reviewed_competition(client, world, n_players=2)
        published = client.post(
            f"/api/competitions/{cid}/rankings/publish", headers=auth(world["super"])
        ).json()
        target = next(r for r in published if r["scope"] == "individual" and r["rank"] == 2)

        resp = client.patch(
            f"/api/competitions/{cid}/rankings/{target['id']}",
            json={"award": "sportsmanship"},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["award"] == "sportsmanship"


class TestTeamRanking:
    def test_team_ranking_averages_by_team(self, client, world):
        team_a = world["team_a"].id
        cid, players = _setup_reviewed_competition(
            client, world, n_players=4, team_ids=[team_a, team_a, None, None]
        )
        resp = client.get(
            f"/api/competitions/{cid}/rankings/preview?scope=team",
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200, resp.text
        rows = resp.json()
        assert len(rows) == 1
        assert rows[0]["team_id"] == team_a
