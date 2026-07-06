from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.organization import Organization, OrgLevel
from app.models.team import Team
from app.models.user import User, UserRole
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationOut,
    OrganizationUpdate,
)
from app.schemas.team import TeamCreate, TeamOut, TeamUpdate

router = APIRouter(prefix="/org", tags=["organization"])

# 可跨分会读取的角色
_GLOBAL_READ_ROLES = {
    UserRole.super_admin,
    UserRole.finance,
    UserRole.event_director,
}


# ---------------------------------------------------------------- 组织（总会/分会）


@router.get("/organizations", response_model=list[OrganizationOut])
def list_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Organization).filter(Organization.is_deleted.is_(False))
    # 理事管理员只能看到总会 + 自己所辖分会
    if current_user.role == UserRole.council_admin and current_user.branch_id:
        query = query.filter(
            (Organization.level == OrgLevel.headquarters)
            | (Organization.id == current_user.branch_id)
        )
    return query.order_by(Organization.id).all()


@router.post(
    "/organizations",
    response_model=OrganizationOut,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    payload: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.super_admin)),
):
    if payload.level == OrgLevel.branch and payload.parent_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="分会必须指定所属总会 parent_id / Branch requires parent_id",
        )
    org = Organization(**payload.model_dump(), created_by=current_user.id)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.put("/organizations/{org_id}", response_model=OrganizationOut)
def update_organization(
    org_id: int,
    payload: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    org = (
        db.query(Organization)
        .filter(Organization.id == org_id, Organization.is_deleted.is_(False))
        .first()
    )
    if org is None:
        raise HTTPException(status_code=404, detail="组织不存在 / Not found")

    # 超级管理员可改任意；理事管理员仅可改本分会
    is_super = current_user.role == UserRole.super_admin
    is_own_branch = (
        current_user.role == UserRole.council_admin
        and current_user.branch_id == org.id
    )
    if not (is_super or is_own_branch):
        raise HTTPException(status_code=403, detail="权限不足 / Forbidden")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(org, field, value)
    org.updated_by = current_user.id
    db.commit()
    db.refresh(org)
    return org


@router.delete("/organizations/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.super_admin)),
):
    from datetime import datetime, timezone

    org = (
        db.query(Organization)
        .filter(Organization.id == org_id, Organization.is_deleted.is_(False))
        .first()
    )
    if org is None:
        raise HTTPException(status_code=404, detail="组织不存在 / Not found")
    # 逻辑删除
    org.is_deleted = True
    org.deleted_by = current_user.id
    org.deleted_at = datetime.now(timezone.utc)
    db.commit()


# ---------------------------------------------------------------- 球队


@router.get("/teams", response_model=list[TeamOut])
def list_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Team).filter(Team.is_deleted.is_(False))
    if current_user.role in _GLOBAL_READ_ROLES:
        pass
    elif current_user.role == UserRole.council_admin and current_user.branch_id:
        query = query.filter(Team.branch_id == current_user.branch_id)
    elif current_user.role == UserRole.team_captain:
        query = query.filter(Team.captain_id == current_user.id)
    # 普通会员可读全部在册球队（公开信息）
    return query.order_by(Team.id).all()


@router.post("/teams", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
def create_team(
    payload: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.super_admin, UserRole.council_admin)
    ),
):
    branch = (
        db.query(Organization)
        .filter(
            Organization.id == payload.branch_id,
            Organization.level == OrgLevel.branch,
            Organization.is_deleted.is_(False),
        )
        .first()
    )
    if branch is None:
        raise HTTPException(status_code=404, detail="分会不存在 / Branch not found")

    # 理事管理员只能在本分会建队
    if (
        current_user.role == UserRole.council_admin
        and current_user.branch_id != payload.branch_id
    ):
        raise HTTPException(status_code=403, detail="只能管理本分会 / Own branch only")

    team = Team(**payload.model_dump(), created_by=current_user.id)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.put("/teams/{team_id}", response_model=TeamOut)
def update_team(
    team_id: int,
    payload: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = (
        db.query(Team).filter(Team.id == team_id, Team.is_deleted.is_(False)).first()
    )
    if team is None:
        raise HTTPException(status_code=404, detail="球队不存在 / Not found")

    is_super = current_user.role == UserRole.super_admin
    is_branch = (
        current_user.role == UserRole.council_admin
        and current_user.branch_id == team.branch_id
    )
    is_captain = (
        current_user.role == UserRole.team_captain and team.captain_id == current_user.id
    )
    if not (is_super or is_branch or is_captain):
        raise HTTPException(status_code=403, detail="权限不足 / Forbidden")

    data = payload.model_dump(exclude_unset=True)
    # 队长不可改队长归属
    if is_captain and not (is_super or is_branch):
        data.pop("captain_id", None)
    for field, value in data.items():
        setattr(team, field, value)
    team.updated_by = current_user.id
    db.commit()
    db.refresh(team)
    return team


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.super_admin, UserRole.council_admin)
    ),
):
    from datetime import datetime, timezone

    team = (
        db.query(Team).filter(Team.id == team_id, Team.is_deleted.is_(False)).first()
    )
    if team is None:
        raise HTTPException(status_code=404, detail="球队不存在 / Not found")
    if (
        current_user.role == UserRole.council_admin
        and current_user.branch_id != team.branch_id
    ):
        raise HTTPException(status_code=403, detail="只能管理本分会 / Own branch only")
    team.is_deleted = True
    team.deleted_by = current_user.id
    team.deleted_at = datetime.now(timezone.utc)
    db.commit()
