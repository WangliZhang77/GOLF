"""数据 scope（分会/球队隔离）辅助工具。

方案要求自上而下做数据隔离：
- 超级管理员：全部数据
- 理事管理员：仅所辖分会数据
- 球队队长：仅本队数据
- 其他角色：默认仅本人相关数据

Phase 1 先提供 scope 描述工具；Phase 2 组织架构落地后，
业务查询用 `scope_of()` 的返回值对 branch_id/team_id 做过滤。
"""

from dataclasses import dataclass

from app.models.user import User, UserRole


@dataclass
class DataScope:
    all_access: bool = False
    branch_id: int | None = None
    team_id: int | None = None
    self_only: bool = False


def scope_of(user: User) -> DataScope:
    if user.role == UserRole.super_admin:
        return DataScope(all_access=True)
    if user.role == UserRole.finance:
        # 财务可跨分会看台账，但对会员隐私脱敏（脱敏在响应层处理）
        return DataScope(all_access=True)
    if user.role == UserRole.event_director:
        return DataScope(all_access=True)
    if user.role == UserRole.council_admin:
        return DataScope(branch_id=user.branch_id)
    if user.role == UserRole.team_captain:
        return DataScope(team_id=user.team_id)
    return DataScope(self_only=True)
