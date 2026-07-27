from datetime import date, timedelta

from tests.conftest import auth


def _create_sponsor(client, world, **overrides):
    payload = {
        "company_name": "测试赞助商",
        "industry": "科技",
        "level": "金牌",
    }
    payload.update(overrides)
    r = client.post("/api/sponsors", json=payload, headers=auth(world["super"]))
    assert r.status_code == 201, r.text
    return r.json()


class TestSponsorCrud:
    def test_create_and_list(self, client, world):
        _create_sponsor(client, world)
        resp = client.get("/api/sponsors", headers=auth(world["member"]))
        assert resp.status_code == 200
        assert any(s["company_name"] == "测试赞助商" for s in resp.json())

    def test_council_admin_can_create(self, client, world):
        resp = client.post(
            "/api/sponsors",
            json={"company_name": "理事创建"},
            headers=auth(world["council_a"]),
        )
        assert resp.status_code == 201, resp.text

    def test_finance_cannot_create(self, client, world):
        resp = client.post(
            "/api/sponsors",
            json={"company_name": "财务尝试"},
            headers=auth(world["finance"]),
        )
        assert resp.status_code == 403

    def test_finance_can_list(self, client, world):
        _create_sponsor(client, world)
        resp = client.get("/api/sponsors", headers=auth(world["finance"]))
        assert resp.status_code == 200

    def test_member_cannot_create(self, client, world):
        resp = client.post(
            "/api/sponsors",
            json={"company_name": "会员尝试"},
            headers=auth(world["member"]),
        )
        assert resp.status_code == 403

    def test_update_sponsor(self, client, world):
        s = _create_sponsor(client, world)
        resp = client.put(
            f"/api/sponsors/{s['id']}",
            json={"is_active": False, "level": "银牌"},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["is_active"] is False
        assert resp.json()["level"] == "银牌"


class TestSponsorContract:
    def test_create_and_list_contract(self, client, world):
        s = _create_sponsor(client, world)
        resp = client.post(
            f"/api/sponsors/{s['id']}/contracts",
            json={
                "amount": "5000.00",
                "start_date": date.today().isoformat(),
                "end_date": (date.today() + timedelta(days=365)).isoformat(),
                "benefit": "赛事横幅展示",
            },
            headers=auth(world["super"]),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["sponsor_id"] == s["id"]

        listed = client.get(f"/api/sponsors/{s['id']}/contracts", headers=auth(world["member"]))
        assert listed.status_code == 200
        assert len(listed.json()) == 1

    def test_contract_can_link_competition(self, client, world):
        s = _create_sponsor(client, world)
        start = (date.today() + timedelta(days=21)).isoformat()
        comp = client.post(
            "/api/competitions",
            json={
                "name": "赞助测试赛",
                "competition_type": "official",
                "branch_id": world["branch_a"].id,
                "start_time": f"{start}T00:00:00Z",
            },
            headers=auth(world["super"]),
        )
        assert comp.status_code == 201, comp.text
        cid = comp.json()["id"]

        resp = client.post(
            f"/api/sponsors/{s['id']}/contracts",
            json={
                "competition_id": cid,
                "amount": "2000.00",
                "start_date": date.today().isoformat(),
            },
            headers=auth(world["super"]),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["competition_id"] == cid

    def test_non_manage_role_cannot_create_contract(self, client, world):
        s = _create_sponsor(client, world)
        resp = client.post(
            f"/api/sponsors/{s['id']}/contracts",
            json={"amount": "1000.00", "start_date": date.today().isoformat()},
            headers=auth(world["finance"]),
        )
        assert resp.status_code == 403

    def test_update_contract(self, client, world):
        s = _create_sponsor(client, world)
        created = client.post(
            f"/api/sponsors/{s['id']}/contracts",
            json={"amount": "1000.00", "start_date": date.today().isoformat()},
            headers=auth(world["super"]),
        ).json()

        resp = client.put(
            f"/api/sponsors/{s['id']}/contracts/{created['id']}",
            json={"amount": "1500.00", "benefit": "更新后的权益"},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["amount"] == "1500.00"
        assert resp.json()["benefit"] == "更新后的权益"
