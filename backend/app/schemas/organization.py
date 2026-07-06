from pydantic import BaseModel, ConfigDict

from app.models.organization import OrgLevel


class OrganizationBase(BaseModel):
    name: str
    region: str | None = None
    registration_no: str | None = None
    charter_file: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None


class OrganizationCreate(OrganizationBase):
    level: OrgLevel = OrgLevel.branch
    parent_id: int | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = None
    region: str | None = None
    registration_no: str | None = None
    charter_file: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    is_active: bool | None = None


class OrganizationOut(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level: OrgLevel
    parent_id: int | None
    is_active: bool
