from datetime import date, datetime, timedelta, timezone

from app.core.security import create_access_token
from tests.conftest import auth


def _token(uid: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(uid)}"}


def _create_member(client, world, username, branch=None, handicap=None, join_date=None):
    payload = {
        "chinese_name": "分析会员",
        "branch_id": (branch or world["branch_a"]).id,
        "account_username": username,
        "account_password": "pw123456",
    }
    if handicap is not None:
        payload["handicap"] = handicap
    if join_date is not None:
        payload["join_date"] = join_date.isoformat()
    resp = client.post("/api/members", json=payload, headers=auth(world["super"]))
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_open_competition(client, world, **overrides):
    start = datetime.now(timezone.utc) + timedelta(days=21)
    payload = {
        "name": "分析测试赛",
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


def _register_and_approve(client, world, cid, username, handicap="10.0"):
    body = _create_member(client, world, username, handicap=handicap)
    uid = body["user_id"]
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


def _build_one_approved_scorecard(client, world):
    """报名/审核/分组/开赛/记满18洞/提交/管理员审核通过，返回 (cid, member_body)。"""
    cid = _create_open_competition(client, world)
    body, uid = _register_and_approve(client, world, cid, "an_score", handicap="10.0")
    client.post(
        f"/api/competitions/{cid}/groups/generate", json={}, headers=auth(world["super"])
    )
    client.post(f"/api/competitions/{cid}/start", headers=auth(world["super"]))
    card = client.get(f"/api/competitions/{cid}/scorecards/mine", headers=_token(uid)).json()
    for h in range(1, 19):
        client.patch(
            f"/api/competitions/{cid}/scorecards/{card['id']}/hole",
            json={"hole_number": h, "strokes": 4},
            headers=_token(uid),
        )
    client.post(f"/api/competitions/{cid}/scorecards/{card['id']}/submit", headers=_token(uid))
    client.post(
        f"/api/competitions/{cid}/scorecards/{card['id']}/admin-review",
        json={"approve": True},
        headers=auth(world["super"]),
    )
    return cid, body


def _create_published_activity(client, world, **overrides):
    start = datetime.now(timezone.utc) + timedelta(days=7)
    payload = {
        "title": "分析测试活动",
        "activity_type": "weekly_round",
        "branch_id": world["branch_a"].id,
        "start_at": start.isoformat(),
        "max_participants": 10,
    }
    payload.update(overrides)
    r = client.post("/api/activities", json=payload, headers=auth(world["super"]))
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    client.post(f"/api/activities/{aid}/publish", headers=auth(world["super"]))
    return aid


class TestRoleAccess:
    def test_team_captain_forbidden(self, client, world):
        resp = client.get("/api/analytics/dashboard", headers=auth(world["captain"]))
        assert resp.status_code == 403

    def test_event_director_forbidden(self, client, world):
        resp = client.get("/api/analytics/dashboard", headers=auth(world["event_director"]))
        assert resp.status_code == 403

    def test_finance_allowed(self, client, world):
        resp = client.get("/api/analytics/dashboard", headers=auth(world["finance"]))
        assert resp.status_code == 200

    def test_council_admin_allowed(self, client, world):
        resp = client.get("/api/analytics/dashboard", headers=auth(world["council_a"]))
        assert resp.status_code == 200


class TestMemberSection:
    def test_counts_and_new_last_30d(self, client, world, db):
        from app.models.member import Member, MemberStatus

        _create_member(client, world, "an_new", branch=world["branch_a"], join_date=date.today())
        sleepy = _create_member(client, world, "an_sleep", branch=world["branch_a"])

        row = db.query(Member).filter(Member.id == sleepy["id"]).first()
        row.status = MemberStatus.sleeping
        db.commit()

        resp = client.get("/api/analytics/dashboard", headers=auth(world["super"]))
        assert resp.status_code == 200, resp.text
        members = resp.json()["members"]
        assert members["new_last_30d"] >= 1
        assert members["sleeping"] >= 1
        assert members["total"] >= 2

    def test_council_admin_scoped_to_own_branch(self, client, world):
        _create_member(client, world, "an_scope_a", branch=world["branch_a"])
        _create_member(client, world, "an_scope_b", branch=world["branch_b"])

        scoped = client.get("/api/analytics/dashboard", headers=auth(world["council_a"])).json()
        full = client.get("/api/analytics/dashboard", headers=auth(world["super"])).json()
        assert scoped["members"]["total"] <= full["members"]["total"]


class TestActivitySection:
    def test_most_attended_and_avg_participants(self, client, world):
        small = _create_published_activity(client, world, title="小活动", max_participants=10)
        big = _create_published_activity(client, world, title="大活动", max_participants=10)

        m1 = _create_member(client, world, "an_act1")
        m2 = _create_member(client, world, "an_act2")
        client.post(f"/api/activities/{big}/register", json={}, headers=_token(m1["user_id"]))
        client.post(f"/api/activities/{big}/register", json={}, headers=_token(m2["user_id"]))

        m3 = _create_member(client, world, "an_act3")
        client.post(f"/api/activities/{small}/register", json={}, headers=_token(m3["user_id"]))

        resp = client.get("/api/analytics/dashboard", headers=auth(world["super"]))
        assert resp.status_code == 200, resp.text
        activities = resp.json()["activities"]
        assert activities["total"] >= 2
        assert activities["most_attended"] is not None
        assert activities["most_attended"]["id"] == big


class TestCompetitionSection:
    def test_avg_net_score_from_approved_card(self, client, world):
        _build_one_approved_scorecard(client, world)
        resp = client.get("/api/analytics/dashboard", headers=auth(world["super"]))
        assert resp.status_code == 200, resp.text
        competitions = resp.json()["competitions"]
        assert competitions["total"] >= 1
        assert competitions["avg_net_score"] is not None
        # handicap 10.0，总杆 72（18洞*4杆）=> net = 62.0
        assert competitions["avg_net_score"] == 62.0

    def test_handicap_change_from_recent_adjustment(self, client, world):
        m = _create_member(client, world, "an_hc", handicap="18.0")
        client.patch(
            f"/api/handicap/members/{m['id']}",
            json={"new_handicap": "15.0"},
            headers=auth(world["super"]),
        )
        resp = client.get("/api/analytics/dashboard", headers=auth(world["super"]))
        competitions = resp.json()["competitions"]
        assert competitions["handicap_change"] is not None
        assert competitions["handicap_change"] < 0


class TestFinanceSection:
    def test_income_expense_profit(self, client, world):
        client.post(
            "/api/finance/ledger",
            json={
                "direction": "income",
                "category": "annual_dues",
                "amount": "200.00",
                "title": "分析财务收入",
                "branch_id": world["branch_a"].id,
                "is_paid": True,
            },
            headers=auth(world["finance"]),
        )
        client.post(
            "/api/finance/ledger",
            json={
                "direction": "expense",
                "category": "admin_expense",
                "amount": "50.00",
                "title": "分析财务支出",
                "branch_id": world["branch_a"].id,
                "is_paid": True,
            },
            headers=auth(world["finance"]),
        )
        resp = client.get("/api/analytics/dashboard", headers=auth(world["super"]))
        finance = resp.json()["finance"]
        assert float(finance["income"]) >= 200.0
        assert float(finance["expense"]) >= 50.0
        assert float(finance["profit"]) == float(finance["income"]) - float(finance["expense"])

    def test_sponsorship_total_from_active_contract(self, client, world):
        sponsor = client.post(
            "/api/sponsors",
            json={"company_name": "分析赞助商"},
            headers=auth(world["super"]),
        ).json()
        client.post(
            f"/api/sponsors/{sponsor['id']}/contracts",
            json={
                "amount": "3000.00",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=30)).isoformat(),
            },
            headers=auth(world["super"]),
        )
        resp = client.get("/api/analytics/dashboard", headers=auth(world["super"]))
        finance = resp.json()["finance"]
        assert float(finance["sponsorship_total"]) >= 3000.0
