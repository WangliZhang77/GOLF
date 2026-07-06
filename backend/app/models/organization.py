import enum

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import AuditMixin, Base


class OrgLevel(str, enum.Enum):
    headquarters = "headquarters"  # 总会
    branch = "branch"              # 分会


class Organization(Base, AuditMixin):
    """协会组织表：总会 → 分会（自引用树）。"""

    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    level: Mapped[OrgLevel] = mapped_column(
        Enum(OrgLevel, name="org_level", native_enum=False, length=16),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )

    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 新西兰社团注册号
    registration_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # 章程/资质文件归档（存储路径或 URL）
    charter_file: Mapped[str | None] = mapped_column(String(512), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
