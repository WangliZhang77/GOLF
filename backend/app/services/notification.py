"""站内消息服务：双语模板，正文不含隐私字段。"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.activity import Activity, ActivityRegistration, RegistrationStatus
from app.models.finance import FinanceLedger, IncomeCategory
from app.models.member import Member
from app.models.notification import MessageType, Notification
from app.services.billing import list_member_outstanding_ledgers, list_outstanding_member_ids


def create_notification(
    db: Session,
    *,
    recipient_user_id: int,
    message_type: MessageType,
    title_zh: str,
    title_en: str,
    body_zh: str,
    body_en: str,
    related_member_id: int | None = None,
    related_activity_id: int | None = None,
    related_ledger_id: int | None = None,
    sent_by: int | None = None,
    created_by: int | None = None,
) -> Notification:
    row = Notification(
        recipient_user_id=recipient_user_id,
        message_type=message_type,
        title_zh=title_zh,
        title_en=title_en,
        body_zh=body_zh,
        body_en=body_en,
        related_member_id=related_member_id,
        related_activity_id=related_activity_id,
        related_ledger_id=related_ledger_id,
        sent_by=sent_by,
        created_by=created_by,
    )
    db.add(row)
    return row


def notify_activity_registered(
    db: Session,
    *,
    activity: Activity,
    member: Member,
    recipient_user_id: int,
) -> Notification:
    title_zh = "活动报名成功"
    title_en = "Activity registration confirmed"
    body_zh = f"您已成功报名活动「{activity.title}」。"
    body_en = f'You have registered for "{activity.title}".'
    return create_notification(
        db,
        recipient_user_id=recipient_user_id,
        message_type=MessageType.activity_registered,
        title_zh=title_zh,
        title_en=title_en,
        body_zh=body_zh,
        body_en=body_en,
        related_member_id=member.id,
        related_activity_id=activity.id,
        created_by=recipient_user_id,
    )


def notify_dues_reminder(
    db: Session,
    *,
    member: Member,
    ledger: FinanceLedger,
    sent_by: int,
) -> Notification | None:
    if member.user_id is None:
        return None
    try:
        cat = IncomeCategory(ledger.category)
        cat_zh = {
            IncomeCategory.annual_dues: "年度会费",
            IncomeCategory.event_registration: "活动报名费",
        }.get(cat, "待缴费用")
        cat_en = {
            IncomeCategory.annual_dues: "annual dues",
            IncomeCategory.event_registration: "event registration fee",
        }.get(cat, "outstanding payment")
    except ValueError:
        cat_zh = "待缴费用"
        cat_en = "outstanding payment"

    title_zh = "会费催缴提醒"
    title_en = "Payment reminder"
    body_zh = (
        f"您有一笔待缴费用（{cat_zh}：{ledger.title}，"
        f"金额 {ledger.currency} {ledger.amount}），请至「我的账单」查看。"
    )
    body_en = (
        f"You have an outstanding {cat_en} ({ledger.title}, "
        f"{ledger.currency} {ledger.amount}). Please check My Bills."
    )
    return create_notification(
        db,
        recipient_user_id=member.user_id,
        message_type=MessageType.dues_reminder,
        title_zh=title_zh,
        title_en=title_en,
        body_zh=body_zh,
        body_en=body_en,
        related_member_id=member.id,
        related_ledger_id=ledger.id,
        sent_by=sent_by,
        created_by=sent_by,
    )


def send_dues_reminders(
    db: Session,
    *,
    sent_by: int,
    member_id: int | None = None,
    all_outstanding: bool = False,
    branch_id: int | None = None,
) -> int:
    sent = 0
    if member_id is not None:
        member = db.query(Member).filter(Member.id == member_id, Member.is_deleted.is_(False)).first()
        if member is None:
            return 0
        for ledger in list_member_outstanding_ledgers(db, member.id):
            if notify_dues_reminder(db, member=member, ledger=ledger, sent_by=sent_by):
                sent += 1
        return sent

    if not all_outstanding:
        return 0

    for mid in list_outstanding_member_ids(db, branch_id=branch_id):
        member = db.query(Member).filter(Member.id == mid).first()
        if member is None:
            continue
        for ledger in list_member_outstanding_ledgers(db, mid):
            if notify_dues_reminder(db, member=member, ledger=ledger, sent_by=sent_by):
                sent += 1
    return sent


def notify_activity_reminder(
    db: Session,
    *,
    activity: Activity,
    member: Member,
    sent_by: int,
) -> Notification | None:
    if member.user_id is None:
        return None
    start_hint = ""
    start_hint_en = ""
    if activity.start_at:
        start_hint = f"开始时间：{activity.start_at.strftime('%Y-%m-%d %H:%M')}。"
        start_hint_en = f"Starts at {activity.start_at.strftime('%Y-%m-%d %H:%M')}."
    title_zh = "活动提醒"
    title_en = "Activity reminder"
    body_zh = f"提醒您即将参加的活动「{activity.title}」。{start_hint}"
    body_en = f'Reminder for upcoming activity "{activity.title}". {start_hint_en}'
    return create_notification(
        db,
        recipient_user_id=member.user_id,
        message_type=MessageType.activity_reminder,
        title_zh=title_zh,
        title_en=title_en,
        body_zh=body_zh,
        body_en=body_en,
        related_member_id=member.id,
        related_activity_id=activity.id,
        sent_by=sent_by,
        created_by=sent_by,
    )


def send_activity_reminders(db: Session, *, activity: Activity, sent_by: int) -> int:
    active = (RegistrationStatus.registered, RegistrationStatus.checked_in)
    regs = (
        db.query(ActivityRegistration)
        .filter(
            ActivityRegistration.activity_id == activity.id,
            ActivityRegistration.status.in_(active),
            ActivityRegistration.is_deleted.is_(False),
        )
        .all()
    )
    seen_users: set[int] = set()
    sent = 0
    for reg in regs:
        member = (
            db.query(Member)
            .filter(Member.id == reg.member_id, Member.is_deleted.is_(False))
            .first()
        )
        if member is None or member.user_id is None or member.user_id in seen_users:
            continue
        seen_users.add(member.user_id)
        if notify_activity_reminder(db, activity=activity, member=member, sent_by=sent_by):
            sent += 1
    return sent


def mark_read(db: Session, notification: Notification) -> None:
    if notification.is_read:
        return
    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)


def mark_all_read(db: Session, user_id: int) -> int:
    rows = (
        db.query(Notification)
        .filter(
            Notification.recipient_user_id == user_id,
            Notification.is_read.is_(False),
            Notification.is_deleted.is_(False),
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    for row in rows:
        row.is_read = True
        row.read_at = now
    return len(rows)
