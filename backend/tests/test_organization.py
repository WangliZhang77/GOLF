from tests.conftest import auth


class TestOrganization:
    def test_super_can_create_branch(self, client, world):
        resp = client.post(
            "/api/org/organizations",
            json={"name": "基督城分会", "level": "branch", "parent_id": world["hq"].id},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 201, resp.text
        assert resp.json()["level"] == "branch"

    def test_member_cannot_create_branch(self, client, world):
        resp = client.post(
            "/api/org/organizations",
            json={"name": "非法分会", "level": "branch", "parent_id": world["hq"].id},
            headers=auth(world["member"]),
        )
        assert resp.status_code == 403

    def test_branch_requires_parent(self, client, world):
        resp = client.post(
            "/api/org/organizations",
            json={"name": "无父分会", "level": "branch"},
            headers=auth(world["super"]),
        )
        assert resp.status_code == 422

    def test_council_admin_only_sees_hq_and_own_branch(self, client, world):
        resp = client.get("/api/org/organizations", headers=auth(world["council_a"]))
        assert resp.status_code == 200
        ids = {o["id"] for o in resp.json()}
        assert world["branch_a"].id in ids
        assert world["hq"].id in ids
        assert world["branch_b"].id not in ids  # 看不到其他分会

    def test_unauthenticated_rejected(self, client):
        resp = client.get("/api/org/organizations")
        assert resp.status_code == 401


class TestTeam:
    def test_council_admin_create_team_in_own_branch(self, client, world):
        resp = client.post(
            "/api/org/teams",
            json={"name": "新队", "branch_id": world["branch_a"].id},
            headers=auth(world["council_a"]),
        )
        assert resp.status_code == 201, resp.text

    def test_council_admin_cannot_create_team_in_other_branch(self, client, world):
        resp = client.post(
            "/api/org/teams",
            json={"name": "越权队", "branch_id": world["branch_b"].id},
            headers=auth(world["council_a"]),
        )
        assert resp.status_code == 403

    def test_team_scope_isolation_on_list(self, client, world):
        # council_b 看不到属于 branch_a 的 team_a
        resp = client.get("/api/org/teams", headers=auth(world["council_b"]))
        assert resp.status_code == 200
        ids = {t["id"] for t in resp.json()}
        assert world["team_a"].id not in ids


class TestEnrollmentFlow:
    def _apply(self, client, world):
        return client.post(
            "/api/org/enrollments/apply",
            json={"team_id": world["team_a"].id, "remark": "想入队"},
            headers=auth(world["member"]),
        )

    def test_full_approval_flow(self, client, world, db):
        # 1. 会员申请
        r1 = self._apply(client, world)
        assert r1.status_code == 201, r1.text
        enr_id = r1.json()["id"]
        assert r1.json()["status"] == "pending_captain"

        # 2. 队长审核通过
        r2 = client.post(
            f"/api/org/enrollments/{enr_id}/captain-review",
            json={"approve": True},
            headers=auth(world["captain"]),
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["status"] == "pending_branch"

        # 3. 分会备案通过
        r3 = client.post(
            f"/api/org/enrollments/{enr_id}/branch-review",
            json={"approve": True},
            headers=auth(world["council_a"]),
        )
        assert r3.status_code == 200, r3.text
        assert r3.json()["status"] == "approved"

        # 备案通过后，申请人主队被设置（跨会话，先过期本地缓存再查）
        from app.models import User

        db.expire_all()
        applicant = db.query(User).filter(User.username == "member").first()
        assert applicant.team_id == world["team_a"].id

    def test_duplicate_application_conflict(self, client, world):
        assert self._apply(client, world).status_code == 201
        assert self._apply(client, world).status_code == 409

    def test_non_captain_cannot_captain_review(self, client, world):
        enr_id = self._apply(client, world).json()["id"]
        # member 自己不能审核
        resp = client.post(
            f"/api/org/enrollments/{enr_id}/captain-review",
            json={"approve": True},
            headers=auth(world["member"]),
        )
        assert resp.status_code == 403

    def test_branch_review_requires_pending_branch_state(self, client, world):
        enr_id = self._apply(client, world).json()["id"]
        # 尚未经队长审核，直接分会备案应拒绝（状态不符）
        resp = client.post(
            f"/api/org/enrollments/{enr_id}/branch-review",
            json={"approve": True},
            headers=auth(world["council_a"]),
        )
        assert resp.status_code == 409

    def test_other_branch_admin_cannot_branch_review(self, client, world):
        enr_id = self._apply(client, world).json()["id"]
        client.post(
            f"/api/org/enrollments/{enr_id}/captain-review",
            json={"approve": True},
            headers=auth(world["captain"]),
        )
        # council_b 不是该队所属分会理事
        resp = client.post(
            f"/api/org/enrollments/{enr_id}/branch-review",
            json={"approve": True},
            headers=auth(world["council_b"]),
        )
        assert resp.status_code == 403
