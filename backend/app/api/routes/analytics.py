from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.analytics import AnalyticsDashboardOut
from app.services.analytics import activity_stats, competition_stats, finance_stats, member_stats

router = APIRouter(prefix="/analytics", tags=["analytics"])

_ALLOWED_ROLES = {UserRole.super_admin, UserRole.council_admin, UserRole.finance}


@router.get("/dashboard", response_model=AnalyticsDashboardOut)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ALLOWED_ROLES)),
):
    branch_id = current_user.branch_id if current_user.role == UserRole.council_admin else None
    return AnalyticsDashboardOut(
        members=member_stats(db, branch_id),
        activities=activity_stats(db, branch_id),
        competitions=competition_stats(db, branch_id),
        finance=finance_stats(db, branch_id),
    )
