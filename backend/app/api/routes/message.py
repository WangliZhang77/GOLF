from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.models.activity import Activity
from app.models.member import Member
from app.models.notification import MessageType, Notification
from app.models.user import User, UserRole
from app.schemas.message import (
    ActivityReminderRequest,
    ActivityReminderResult,
    DuesReminderRequest,
    DuesReminderResult,
    NotificationOut,
    UnreadCountOut,
)
from app.services.notification import (
    mark_all_read,
    mark_read,
    send_activity_reminders,
    send_dues_reminders,
)

router = APIRouter(prefix="/messages", tags=["messages"])


def _get_notification_for_user(
    db: Session, notification_id: int, user_id: int
) -> Notification:
    row = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.recipient_user_id == user_id,
            Notification.is_deleted.is_(False),
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="消息不存在 / Message not found")
    return row


def _sent_query_for_user(db: Session, user: User):
    """管理端查看已发送记录（按 sent_by 或全量）。"""
    q = db.query(Notification).filter(Notification.is_deleted.is_(False))
    if user.role == UserRole.super_admin:
        return q
    if user.role == UserRole.finance:
        return q.filter(
            Notification.message_type.in_(
                [MessageType.dues_reminder, MessageType.system]
            )
        )
    if user.role == UserRole.council_admin and user.branch_id:
        member_ids = [
            m.id
            for m in db.query(Member.id)
            .filter(Member.branch_id == user.branch_id, Member.is_deleted.is_(False))
            .all()
        ]
        if not member_ids:
            return q.filter(False)
        return q.filter(Notification.related_member_id.in_(member_ids))
    return q.filter(False)


@router.get("/me", response_model=list[NotificationOut])
def my_messages(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Notification).filter(
        Notification.recipient_user_id == current_user.id,
        Notification.is_deleted.is_(False),
    )
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    return q.order_by(Notification.id.desc()).all()


@router.get("/me/unread-count", response_model=UnreadCountOut)
def my_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = (
        db.query(Notification)
        .filter(
            Notification.recipient_user_id == current_user.id,
            Notification.is_read.is_(False),
            Notification.is_deleted.is_(False),
        )
        .count()
    )
    return UnreadCountOut(count=count)


@router.post("/me/{notification_id}/read", response_model=NotificationOut)
def read_message(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = _get_notification_for_user(db, notification_id, current_user.id)
    mark_read(db, row)
    row.updated_by = current_user.id
    db.commit()
    db.refresh(row)
    return row


@router.post("/me/read-all")
def read_all_messages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = mark_all_read(db, current_user.id)
    db.commit()
    return {"marked_read": count}


@router.get("", response_model=list[NotificationOut])
def list_sent_messages(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.super_admin, UserRole.finance, UserRole.council_admin)
    ),
):
    return (
        _sent_query_for_user(db, current_user)
        .order_by(Notification.id.desc())
        .limit(limit)
        .all()
    )


@router.post("/dues-reminder", response_model=DuesReminderResult)
def dues_reminder(
    body: DuesReminderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.super_admin, UserRole.finance)),
):
    if body.member_id is None and not body.all_outstanding:
        raise HTTPException(
            status_code=400,
            detail="请指定 member_id 或 all_outstanding / Specify member or batch",
        )
    branch_id = body.branch_id
    if current_user.role == UserRole.finance and body.all_outstanding:
        branch_id = None

    sent = send_dues_reminders(
        db,
        sent_by=current_user.id,
        member_id=body.member_id,
        all_outstanding=body.all_outstanding,
        branch_id=branch_id,
    )
    db.commit()
    return DuesReminderResult(sent_count=sent)


@router.post("/activity-reminder", response_model=ActivityReminderResult)
def activity_reminder(
    body: ActivityReminderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.super_admin,
            UserRole.council_admin,
            UserRole.event_director,
        )
    ),
):
    activity = (
        db.query(Activity)
        .filter(Activity.id == body.activity_id, Activity.is_deleted.is_(False))
        .first()
    )
    if activity is None:
        raise HTTPException(status_code=404, detail="活动不存在 / Activity not found")
    if (
        current_user.role == UserRole.council_admin
        and current_user.branch_id
        and activity.branch_id != current_user.branch_id
    ):
        raise HTTPException(status_code=403, detail="权限不足 / Forbidden")

    sent = send_activity_reminders(db, activity=activity, sent_by=current_user.id)
    db.commit()
    return ActivityReminderResult(sent_count=sent)
