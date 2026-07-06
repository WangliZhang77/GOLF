from datetime import date

from pydantic import BaseModel, ConfigDict


class TeamBase(BaseModel):
    name: str
    home_course: str | None = None
    logo: str | None = None
    charter: str | None = None
    founded_date: date | None = None


class TeamCreate(TeamBase):
    branch_id: int
    captain_id: int | None = None


class TeamUpdate(BaseModel):
    name: str | None = None
    home_course: str | None = None
    logo: str | None = None
    charter: str | None = None
    founded_date: date | None = None
    captain_id: int | None = None
    is_active: bool | None = None


class TeamOut(TeamBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    branch_id: int
    captain_id: int | None
    is_active: bool
