from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enrollment import EnrollmentStatus


class EnrollmentApply(BaseModel):
    team_id: int
    remark: str | None = None


class EnrollmentReview(BaseModel):
    approve: bool
    remark: str | None = None


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    team_id: int
    user_id: int
    status: EnrollmentStatus
    captain_reviewed_by: int | None
    captain_reviewed_at: datetime | None
    branch_reviewed_by: int | None
    branch_reviewed_at: datetime | None
    remark: str | None
