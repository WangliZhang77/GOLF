import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import Base, Organization, OrgLevel, Team, User, UserRole


@pytest.fixture()
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db(session_factory) -> Session:
    s = session_factory()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_user(db, username, role, branch_id=None, team_id=None):
    user = User(
        username=username,
        full_name=username,
        hashed_password=hash_password("pw123456"),
        role=role,
        is_active=True,
        branch_id=branch_id,
        team_id=team_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


@pytest.fixture()
def world(db):
    """搭建基础组织与各角色用户，返回便于测试引用的对象集合。"""
    hq = Organization(name="总会", level=OrgLevel.headquarters)
    db.add(hq)
    db.commit()
    db.refresh(hq)

    branch_a = Organization(name="奥克兰分会", level=OrgLevel.branch, parent_id=hq.id)
    branch_b = Organization(name="惠灵顿分会", level=OrgLevel.branch, parent_id=hq.id)
    db.add_all([branch_a, branch_b])
    db.commit()
    db.refresh(branch_a)
    db.refresh(branch_b)

    superuser = _make_user(db, "super", UserRole.super_admin)
    council_a = _make_user(db, "council_a", UserRole.council_admin, branch_id=branch_a.id)
    council_b = _make_user(db, "council_b", UserRole.council_admin, branch_id=branch_b.id)
    captain = _make_user(db, "captain", UserRole.team_captain)
    event_director = _make_user(db, "director", UserRole.event_director)
    finance_user = _make_user(db, "finance", UserRole.finance)
    member = _make_user(db, "member", UserRole.member)

    team_a = Team(name="A队", branch_id=branch_a.id, captain_id=captain.id)
    db.add(team_a)
    db.commit()
    db.refresh(team_a)

    return {
        "hq": hq,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "super": superuser,
        "council_a": council_a,
        "council_b": council_b,
        "captain": captain,
        "event_director": event_director,
        "finance": finance_user,
        "member": member,
        "team_a": team_a,
    }
