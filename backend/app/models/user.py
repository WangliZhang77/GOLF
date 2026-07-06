import enum

from sqlalchemy import Boolean, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class UserRole(str, enum.Enum):
    """方案定义的 6 级角色（自上而下做数据隔离）。"""

    super_admin = "super_admin"        # 超级管理员（协会主席/秘书长）
    council_admin = "council_admin"    # 理事管理员（分会负责人）
    team_captain = "team_captain"      # 球队队长
    event_director = "event_director"  # 赛事总监 & 计分裁判
    finance = "finance"                # 协会财务专员
    member = "member"                  # 普通会员


class User(Base, AuditMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False, length=32),
        default=UserRole.member,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 数据 scope：理事管理员绑定分会、球队队长绑定球队。
    # Phase 1 先作为可空整型占位，Phase 2 组织架构落地后再加外键约束。
    branch_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    team_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
