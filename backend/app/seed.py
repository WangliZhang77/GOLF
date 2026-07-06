"""初始化种子数据：创建默认超级管理员。

用法：
    python -m app.seed
默认账号见 .env 的 FIRST_SUPERUSER_* 配置。
"""

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from datetime import date, datetime, timedelta, timezone

from app.models.activity import (
    Activity,
    ActivityRegistration,
    ActivityStatus,
    ActivityType,
    RegistrantType,
    RegistrationStatus,
)
from app.models.finance import (
    FinanceLedger,
    IncomeCategory,
    LedgerDirection,
    LedgerStatus,
    PaymentMethod,
)
from app.models.member import Member, MemberLevel, MemberStatus
from app.models.organization import Organization, OrgLevel
from app.models.team import Team
from app.models.user import User, UserRole
from app.models.notification import MessageType, Notification


DEMO_PASSWORD = "demo123456"


def _get_or_create_user(db, *, username, full_name, role, branch_id=None, team_id=None):
    """幂等创建演示用户，返回用户对象。"""
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return existing
    user = User(
        username=username,
        full_name=full_name,
        hashed_password=hash_password(DEMO_PASSWORD),
        role=role,
        is_active=True,
        branch_id=branch_id,
        team_id=team_id,
    )
    db.add(user)
    db.flush()
    print(f"已创建演示账号：{username} / {DEMO_PASSWORD}（{role.value}）")
    return user


def create_headquarters(db) -> None:
    exists = (
        db.query(Organization)
        .filter(Organization.level == OrgLevel.headquarters)
        .first()
    )
    if exists:
        print(f"总会已存在，跳过：{exists.name}")
        return
    hq = Organization(
        name="新西兰华人高尔夫协会总会",
        level=OrgLevel.headquarters,
        region="New Zealand",
    )
    db.add(hq)
    db.commit()
    print("已创建总会：新西兰华人高尔夫协会总会")


def create_first_superuser() -> None:
    db = SessionLocal()
    try:
        existing = (
            db.query(User)
            .filter(User.username == settings.first_superuser_username)
            .first()
        )
        if existing:
            print(f"超级管理员已存在，跳过：{existing.username}")
            return

        user = User(
            username=settings.first_superuser_username,
            full_name=settings.first_superuser_full_name,
            hashed_password=hash_password(settings.first_superuser_password),
            role=UserRole.super_admin,
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(
            "已创建超级管理员："
            f"{settings.first_superuser_username} / {settings.first_superuser_password}"
        )
    finally:
        db.close()


def create_demo_world(db) -> None:
    """创建演示组织架构（分会/球队）与多角色演示账号，保证幂等。"""
    hq = (
        db.query(Organization)
        .filter(Organization.level == OrgLevel.headquarters)
        .first()
    )
    if not hq:
        print("无总会，跳过演示世界")
        return

    branch = (
        db.query(Organization)
        .filter(
            Organization.level == OrgLevel.branch,
            Organization.name == "奥克兰分会",
        )
        .first()
    )
    if not branch:
        branch = Organization(
            name="奥克兰分会",
            level=OrgLevel.branch,
            parent_id=hq.id,
            region="Auckland",
        )
        db.add(branch)
        db.flush()
        print("已创建演示分会：奥克兰分会")

    # 多角色账号
    _get_or_create_user(
        db, username="finance", full_name="财务专员", role=UserRole.finance
    )
    _get_or_create_user(
        db,
        username="council",
        full_name="奥克兰分会理事",
        role=UserRole.council_admin,
        branch_id=branch.id,
    )
    captain = _get_or_create_user(
        db, username="captain", full_name="A队队长", role=UserRole.team_captain
    )

    team = (
        db.query(Team)
        .filter(Team.name == "奥克兰A队", Team.branch_id == branch.id)
        .first()
    )
    if not team:
        team = Team(
            name="奥克兰A队",
            branch_id=branch.id,
            captain_id=captain.id,
            home_course="Demo Golf Course",
        )
        db.add(team)
        db.flush()
        print("已创建演示球队：奥克兰A队")

    db.commit()


def create_demo_member(db) -> None:
    """创建演示会员账号 + 档案，便于会员端联调。"""
    username = "demo"
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        print(f"演示会员已存在，跳过：{username}")
        return

    branch = (
        db.query(Organization)
        .filter(Organization.level == OrgLevel.branch)
        .first()
    )
    team = db.query(Team).filter(Team.name == "奥克兰A队").first()

    user = User(
        username=username,
        full_name="演示会员",
        hashed_password=hash_password(DEMO_PASSWORD),
        role=UserRole.member,
        is_active=True,
        branch_id=branch.id if branch else None,
        team_id=team.id if team else None,
    )
    db.add(user)
    db.flush()

    member = Member(
        user_id=user.id,
        chinese_name="演示会员",
        english_name="Demo Member",
        golf_age=5,
        club_number="NZ-001",
        handicap=18.0,
        nz_address="1 Queen St, Auckland",
        local_phone="+64210000001",
        passport_no="NZ-DEMO-001",
        level=MemberLevel.probationary,
        status=MemberStatus.active,
        branch_id=branch.id if branch else None,
        team_id=team.id if team else None,
        # 入会满 3 个月，便于转正演示（满足时长门槛）
        join_date=date.today() - timedelta(days=120),
        last_active_at=datetime.now(timezone.utc),
        created_by=user.id,
    )
    db.add(member)
    db.commit()
    print(f"已创建演示会员：{username} / {DEMO_PASSWORD}")


def create_demo_activity(db) -> None:
    """创建一条已发布的演示活动，便于会员端报名联调。"""
    exists = db.query(Activity).filter(Activity.title == "演示周末下场").first()
    if exists:
        print("演示活动已存在，跳过")
        return
    branch = (
        db.query(Organization)
        .filter(Organization.level == OrgLevel.branch)
        .first()
    )
    if not branch:
        print("无分会，跳过演示活动")
        return
    act = Activity(
        title="演示周末下场",
        description="Phase 4 活动管理演示：会员可报名、家属可随行、现场扫码签到",
        activity_type=ActivityType.weekly_round,
        status=ActivityStatus.published,
        branch_id=branch.id,
        course_name="Demo Golf Course",
        start_at=datetime.now(timezone.utc) + timedelta(days=3),
        max_participants=20,
        max_family_slots=2,
        family_allowed=True,
        simple_scoring_enabled=True,
    )
    db.add(act)
    db.commit()
    print("已创建演示活动：演示周末下场（已发布）")


def create_demo_finance(db) -> None:
    """为演示会员创建会费流水，便于账单联调。"""
    member = db.query(Member).filter(Member.chinese_name == "演示会员").first()
    if not member:
        print("无演示会员，跳过财务流水")
        return
    exists = (
        db.query(FinanceLedger)
        .filter(
            FinanceLedger.member_id == member.id,
            FinanceLedger.title == "2026 年度会费（待缴）",
        )
        .first()
    )
    if exists:
        print("演示财务流水已存在，跳过")
        return

    admin = (
        db.query(User)
        .filter(User.username == settings.first_superuser_username)
        .first()
    )
    creator = admin.id if admin else None

    db.add(
        FinanceLedger(
            direction=LedgerDirection.income,
            category=IncomeCategory.annual_dues.value,
            amount=120,
            title="2026 年度会费（待缴）",
            member_id=member.id,
            branch_id=member.branch_id,
            is_paid=False,
            status=LedgerStatus.confirmed,
            payment_method=PaymentMethod.manual,
            created_by=creator,
        )
    )
    db.add(
        FinanceLedger(
            direction=LedgerDirection.income,
            category=IncomeCategory.annual_dues.value,
            amount=100,
            title="2025 年度会费",
            member_id=member.id,
            branch_id=member.branch_id,
            is_paid=True,
            status=LedgerStatus.confirmed,
            payment_method=PaymentMethod.bank_transfer,
            created_by=creator,
        )
    )
    db.add(
        FinanceLedger(
            direction=LedgerDirection.expense,
            category="admin_expense",
            amount=85,
            title="协会行政办公开支",
            branch_id=member.branch_id,
            is_paid=True,
            status=LedgerStatus.confirmed,
            payment_method=PaymentMethod.manual,
            created_by=creator,
        )
    )
    db.commit()
    print("已创建演示财务流水：待缴会费 + 已缴历史 + 行政支出")


def create_demo_messages(db) -> None:
    """为演示会员插入站内消息样例。"""
    member = db.query(Member).filter(Member.chinese_name == "演示会员").first()
    if not member or not member.user_id:
        print("无演示会员，跳过演示消息")
        return
    exists = (
        db.query(Notification)
        .filter(
            Notification.recipient_user_id == member.user_id,
            Notification.title_zh == "会费催缴提醒",
        )
        .first()
    )
    if exists:
        print("演示消息已存在，跳过")
        return

    activity = db.query(Activity).filter(Activity.title == "演示周末下场").first()
    admin = (
        db.query(User)
        .filter(User.username == settings.first_superuser_username)
        .first()
    )
    creator = admin.id if admin else None

    db.add(
        Notification(
            recipient_user_id=member.user_id,
            message_type=MessageType.dues_reminder,
            title_zh="会费催缴提醒",
            title_en="Payment reminder",
            body_zh="您有一笔待缴费用（年度会费：2026 年度会费（待缴）），请至「我的账单」查看。",
            body_en="You have an outstanding annual dues. Please check My Bills.",
            related_member_id=member.id,
            sent_by=creator,
            created_by=creator,
        )
    )
    db.add(
        Notification(
            recipient_user_id=member.user_id,
            message_type=MessageType.activity_registered,
            title_zh="活动报名成功",
            title_en="Activity registration confirmed",
            body_zh=f"您已成功报名活动「{activity.title if activity else '演示周末下场'}」。",
            body_en=f'You have registered for "{activity.title if activity else "Demo round"}".',
            related_member_id=member.id,
            related_activity_id=activity.id if activity else None,
            created_by=creator,
        )
    )
    db.commit()
    print("已创建演示站内消息：催缴 + 报名成功")


def create_demo_attendance(db) -> None:
    """为演示会员补 5 条历史签到，满足转正出勤门槛（≥5 次）。"""
    member = db.query(Member).filter(Member.chinese_name == "演示会员").first()
    if not member:
        print("无演示会员，跳过出勤样例")
        return
    branch = db.query(Organization).filter(Organization.level == OrgLevel.branch).first()
    if not branch:
        print("无分会，跳过出勤样例")
        return

    existing = (
        db.query(ActivityRegistration)
        .filter(
            ActivityRegistration.member_id == member.id,
            ActivityRegistration.status == RegistrationStatus.checked_in,
        )
        .count()
    )
    if existing >= 5:
        print("演示出勤样例已存在，跳过")
        return

    admin = (
        db.query(User)
        .filter(User.username == settings.first_superuser_username)
        .first()
    )
    creator = admin.id if admin else None

    for i in range(5):
        act = Activity(
            title=f"历史出勤活动 {i + 1}",
            activity_type=ActivityType.weekly_round,
            status=ActivityStatus.closed,
            branch_id=branch.id,
            course_name="Demo Golf Course",
            start_at=datetime.now(timezone.utc) - timedelta(days=(i + 1) * 14),
            max_participants=20,
            created_by=creator,
        )
        db.add(act)
        db.flush()
        db.add(
            ActivityRegistration(
                activity_id=act.id,
                member_id=member.id,
                user_id=member.user_id,
                registrant_type=RegistrantType.member,
                status=RegistrationStatus.checked_in,
                checked_in_at=act.start_at,
                created_by=creator,
            )
        )
    db.commit()
    print("已创建演示出勤样例：5 次历史签到")


def create_demo_registration(db) -> None:
    """让演示会员已报名「演示周末下场」，会员端活动 Tab 打开即有数据。"""
    member = db.query(Member).filter(Member.chinese_name == "演示会员").first()
    activity = db.query(Activity).filter(Activity.title == "演示周末下场").first()
    if not member or not activity:
        print("缺演示会员或演示活动，跳过报名样例")
        return
    exists = (
        db.query(ActivityRegistration)
        .filter(
            ActivityRegistration.activity_id == activity.id,
            ActivityRegistration.member_id == member.id,
            ActivityRegistration.registrant_type == RegistrantType.member,
        )
        .first()
    )
    if exists:
        print("演示报名样例已存在，跳过")
        return
    db.add(
        ActivityRegistration(
            activity_id=activity.id,
            member_id=member.id,
            user_id=member.user_id,
            registrant_type=RegistrantType.member,
            status=RegistrationStatus.registered,
            created_by=member.user_id,
        )
    )
    db.commit()
    print("已创建演示报名样例：演示会员报名「演示周末下场」")


def seed_all() -> None:
    create_first_superuser()
    db = SessionLocal()
    try:
        create_headquarters(db)
        create_demo_world(db)
        create_demo_member(db)
        create_demo_activity(db)
        create_demo_finance(db)
        create_demo_messages(db)
        create_demo_attendance(db)
        create_demo_registration(db)
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
