"""出勤统计服务：供活动模块与会员转正联动。"""

from sqlalchemy.orm import Session

from app.models.activity import ActivityRegistration, RegistrantType, RegistrationStatus

# 方案：预备会员转正需累计出勤≥5次
PROMOTE_MIN_ATTENDANCE = 5


def count_member_checkins(db: Session, member_id: int) -> int:
    """统计会员本人已签到次数（不含家属行）。"""
    return (
        db.query(ActivityRegistration)
        .filter(
            ActivityRegistration.member_id == member_id,
            ActivityRegistration.registrant_type == RegistrantType.member,
            ActivityRegistration.status == RegistrationStatus.checked_in,
            ActivityRegistration.is_deleted.is_(False),
        )
        .count()
    )
