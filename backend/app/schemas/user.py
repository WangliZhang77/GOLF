from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str | None = None
    full_name: str | None = None
    role: UserRole
    is_active: bool
    branch_id: int | None = None
    team_id: int | None = None


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str | None = None
    email: str | None = None
    role: UserRole = UserRole.member
    branch_id: int | None = None
    team_id: int | None = None
