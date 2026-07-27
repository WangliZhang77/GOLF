from datetime import datetime, timedelta, timezone

from app.core.security import create_access_token
from tests.conftest import auth


def _create_open_competition(client, world, **overrides):
    start = datetime.now(timezone.utc) + timedelta(days=21)
    payload = {
        "name": "计分测试赛",
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
        "chinese_name": "计分会员",
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


def _setup_started_competition(client, world, n_players=4, group_size=4, handicap="12.0"):
    """报名+审核 n 位会员，分组并开始比赛，返回 (cid, [(member_body, uid), ...])。"""
    cid = _create_open_competition(client, world)
    players = [
        _register_and_approve(client, world, cid, f"sc{i}", handicap=handicap)
        for i in range(n_players)
    ]
    client.post(
        f"/api/competitions/{cid}/groups/generate",
        json={"group_size": group_size},
        headers=auth(world["super"]),
    )
    start = client.post(f"/api/competitions/{cid}/start", headers=auth(world["super"]))
    assert start.status_code == 200, start.text
    return cid, players


def _get_card_for_member(client, cid, uid) -> dict:
    r = client.get(f"/api/competitions/{cid}/scorecards/mine", headers=_token(uid))
    assert r.status_code == 200, r.text
    return r.json()


def _fill_holes(client, cid, card_id, headers, value=4, count=18):
    last = None
    for h in range(1, count + 1):
        last = client.patch(
            f"/api/competitions/{cid}/scorecards/{card_id}/hole",
            json={"hole_number": h, "strokes": value},
            headers=headers,
        )
        assert last.status_code == 200, last.text
    return last.json()


class TestHoleEntry:
    def test_owner_can_fill_holes_and_recompute(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=1, handicap="12.0")
        _, uid = players[0]
        card = _get_card_for_member(client, cid, uid)
        result = _fill_holes(client, cid, card["id"], _token(uid), value=4)
        assert result["out_score"] == 36
        assert result["in_score"] == 36
        assert result["total_score"] == 72
        assert float(result["net_score"]) == 60.0

    def test_owner_cannot_edit_after_submit(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=1)
        _, uid = players[0]
        card = _get_card_for_member(client, cid, uid)
        _fill_holes(client, cid, card["id"], _token(uid))
        submit = client.post(
            f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid)
        )
        assert submit.status_code == 200, submit.text

        resp = client.patch(
            f"/api/competitions/{cid}/scorecards/{card['id']}/hole",
            json={"hole_number": 1, "strokes": 5},
            headers=_token(uid),
        )
        assert resp.status_code == 409

    def test_non_owner_cannot_edit(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=2)
        _, uid_a = players[0]
        _, uid_b = players[1]
        card = _get_card_for_member(client, cid, uid_a)
        resp = client.patch(
            f"/api/competitions/{cid}/scorecards/{card['id']}/hole",
            json={"hole_number": 1, "strokes": 4},
            headers=_token(uid_b),
        )
        assert resp.status_code == 403

    def test_manage_role_can_override_regardless_of_status(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=1)
        _, uid = players[0]
        card = _get_card_for_member(client, cid, uid)
        _fill_holes(client, cid, card["id"], _token(uid))
        client.post(f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid))

        resp = client.patch(
            f"/api/competitions/{cid}/scorecards/{card['id']}/hole",
            json={"hole_number": 1, "strokes": 6},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["hole1"] == 6


class TestSubmit:
    def test_submit_requires_all_18_holes(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=1)
        _, uid = players[0]
        card = _get_card_for_member(client, cid, uid)
        _fill_holes(client, cid, card["id"], _token(uid), count=17)
        resp = client.post(
            f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid)
        )
        assert resp.status_code == 422

    def test_submit_success(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=1)
        _, uid = players[0]
        card = _get_card_for_member(client, cid, uid)
        _fill_holes(client, cid, card["id"], _token(uid))
        resp = client.post(
            f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid)
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "submitted"


class TestPeerConfirm:
    def test_peer_confirm_moves_to_checking(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=2)
        _, uid_a = players[0]
        _, uid_b = players[1]
        card = _get_card_for_member(client, cid, uid_a)
        _fill_holes(client, cid, card["id"], _token(uid_a))
        client.post(f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid_a))

        resp = client.post(
            f"/api/competitions/{cid}/scorecards/{card['id']}/peer-confirm",
            json={"comment": "看起来没问题"},
            headers=_token(uid_b),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "checking"

    def test_cannot_confirm_own_card(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=1)
        _, uid = players[0]
        card = _get_card_for_member(client, cid, uid)
        _fill_holes(client, cid, card["id"], _token(uid))
        client.post(f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid))
        resp = client.post(
            f"/api/competitions/{cid}/scorecards/{card['id']}/peer-confirm",
            json={},
            headers=_token(uid),
        )
        assert resp.status_code == 403

    def test_non_groupmate_cannot_confirm(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=1)
        _, uid_owner = players[0]
        card = _get_card_for_member(client, cid, uid_owner)
        _fill_holes(client, cid, card["id"], _token(uid_owner))
        client.post(
            f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid_owner)
        )

        _, uid_outsider = _member_with_profile(client, world, "sc_outsider")
        resp = client.post(
            f"/api/competitions/{cid}/scorecards/{card['id']}/peer-confirm",
            json={},
            headers=_token(uid_outsider),
        )
        assert resp.status_code == 403


class TestAdminReview:
    def test_admin_approve_from_submitted(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=1)
        _, uid = players[0]
        card = _get_card_for_member(client, cid, uid)
        _fill_holes(client, cid, card["id"], _token(uid))
        client.post(f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid))

        resp = client.post(
            f"/api/competitions/{cid}/scorecards/{card['id']}/admin-review",
            json={"approve": True, "comment": "确认无误"},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "approved"

    def test_admin_reject_unlocks_for_resubmit(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=1)
        _, uid = players[0]
        card = _get_card_for_member(client, cid, uid)
        _fill_holes(client, cid, card["id"], _token(uid))
        client.post(f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid))

        reject = client.post(
            f"/api/competitions/{cid}/scorecards/{card['id']}/admin-review",
            json={"approve": False, "comment": "第1洞记录有误"},
            headers=auth(world["super"]),
        )
        assert reject.status_code == 200
        assert reject.json()["status"] == "rejected"

        fix = client.patch(
            f"/api/competitions/{cid}/scorecards/{card['id']}/hole",
            json={"hole_number": 1, "strokes": 5},
            headers=_token(uid),
        )
        assert fix.status_code == 200, fix.text

        resubmit = client.post(
            f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid)
        )
        assert resubmit.status_code == 200
        assert resubmit.json()["status"] == "submitted"

    def test_admin_review_requires_manage_role(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=1)
        _, uid = players[0]
        card = _get_card_for_member(client, cid, uid)
        _fill_holes(client, cid, card["id"], _token(uid))
        client.post(f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid))

        resp = client.post(
            f"/api/competitions/{cid}/scorecards/{card['id']}/admin-review",
            json={"approve": True},
            headers=auth(world["captain"]),
        )
        assert resp.status_code == 403


class TestClosePlay:
    def test_close_play_blocked_with_draft_cards(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=2)
        _, uid = players[0]
        card = _get_card_for_member(client, cid, uid)
        _fill_holes(client, cid, card["id"], _token(uid))
        client.post(f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid))

        resp = client.post(f"/api/competitions/{cid}/close-play", headers=auth(world["super"]))
        assert resp.status_code == 409

    def test_close_play_succeeds_when_all_submitted(self, client, world):
        cid, players = _setup_started_competition(client, world, n_players=2)
        for _, uid in players:
            card = _get_card_for_member(client, cid, uid)
            _fill_holes(client, cid, card["id"], _token(uid))
            client.post(
                f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid)
            )

        resp = client.post(f"/api/competitions/{cid}/close-play", headers=auth(world["super"]))
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "review"
