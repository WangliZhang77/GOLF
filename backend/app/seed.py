"""初始化种子数据：创建默认超级管理员 + 演示数据（英文演示内容，用于对外展示）。

用法：
    python -m app.seed
默认账号见 .env 的 FIRST_SUPERUSER_* 配置。
"""

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from app.models.activity import (
    Activity,
    ActivityRegistration,
    ActivityStatus,
    ActivityType,
    RegistrantType,
    RegistrationStatus,
)
from app.models.competition import (
    Competition,
    CompetitionRegApprovalStatus,
    CompetitionRegistration,
    CompetitionRegPaymentStatus,
    CompetitionStatus,
    CompetitionType,
)
from app.models.course import Course
from app.models.grouping import CompetitionGroup, CompetitionGroupPlayer, GroupStatus
from app.models.handicap import HandicapHistory, HandicapSource
from app.models.ranking import Ranking
from app.models.scorecard import ScoreCard, ScoreCardStatus, ScoreReview, ScoreReviewStatus
from app.models.sponsor import Sponsor, SponsorContract
from app.services.grouping import GroupingPlayer, generate_groups
from app.services.ranking import compute_individual_rankings, compute_team_rankings
from app.services.scoring import recompute_scores
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
        name="NZ Chinese Golf Association Headquarters",
        level=OrgLevel.headquarters,
        region="New Zealand",
    )
    db.add(hq)
    db.commit()
    print("已创建总会：NZ Chinese Golf Association Headquarters")


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
            Organization.name == "Auckland Branch",
        )
        .first()
    )
    if not branch:
        branch = Organization(
            name="Auckland Branch",
            level=OrgLevel.branch,
            parent_id=hq.id,
            region="Auckland",
        )
        db.add(branch)
        db.flush()
        print("已创建演示分会：Auckland Branch")

    # 多角色账号
    _get_or_create_user(
        db, username="finance", full_name="Finance Officer", role=UserRole.finance
    )
    _get_or_create_user(
        db,
        username="council",
        full_name="Auckland Branch Council Admin",
        role=UserRole.council_admin,
        branch_id=branch.id,
    )
    captain = _get_or_create_user(
        db, username="captain", full_name="Team A Captain", role=UserRole.team_captain
    )
    _get_or_create_user(
        db,
        username="director",
        full_name="Event Director",
        role=UserRole.event_director,
    )

    team = (
        db.query(Team)
        .filter(Team.name == "Auckland Team A", Team.branch_id == branch.id)
        .first()
    )
    if not team:
        team = Team(
            name="Auckland Team A",
            branch_id=branch.id,
            captain_id=captain.id,
            home_course="Auckland Fairways Golf Club",
        )
        db.add(team)
        db.flush()
        print("已创建演示球队：Auckland Team A")

    db.commit()


def create_demo_team_b(db) -> None:
    """创建第二支演示球队，用于球队排名对比展示。"""
    branch = (
        db.query(Organization)
        .filter(Organization.level == OrgLevel.branch)
        .first()
    )
    if not branch:
        print("无分会，跳过 Team B")
        return
    exists = (
        db.query(Team)
        .filter(Team.name == "Auckland Team B", Team.branch_id == branch.id)
        .first()
    )
    if exists:
        print("Team B 已存在，跳过")
        return
    db.add(
        Team(
            name="Auckland Team B",
            branch_id=branch.id,
            home_course="Auckland Fairways Golf Club",
        )
    )
    db.commit()
    print("已创建演示球队：Auckland Team B")


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
    team = db.query(Team).filter(Team.name == "Auckland Team A").first()

    user = User(
        username=username,
        full_name="Alex Chen",
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
        chinese_name="Alex Chen",
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


# (username, full_name, team_name, handicap, target_gross_score_for_completed_tournament)
_EXTRA_MEMBERS = [
    ("jordan", "Jordan Lee", "Auckland Team A", "12.0", 80),
    ("morgan", "Morgan Smith", "Auckland Team B", "22.0", 95),
    ("taylor", "Taylor Kim", "Auckland Team B", "15.0", 90),
]


def create_demo_extra_members(db) -> None:
    """创建另外三名演示会员，用于填充一场"已完结"赛事的分组/计分/排名演示。"""
    branch = (
        db.query(Organization)
        .filter(Organization.level == OrgLevel.branch)
        .first()
    )
    if not branch:
        print("无分会，跳过额外演示会员")
        return

    for username, full_name, team_name, handicap, _ in _EXTRA_MEMBERS:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            continue
        team = db.query(Team).filter(Team.name == team_name).first()
        user = User(
            username=username,
            full_name=full_name,
            hashed_password=hash_password(DEMO_PASSWORD),
            role=UserRole.member,
            is_active=True,
            branch_id=branch.id,
            team_id=team.id if team else None,
        )
        db.add(user)
        db.flush()
        db.add(
            Member(
                user_id=user.id,
                chinese_name=full_name,
                handicap=Decimal(handicap),
                level=MemberLevel.formal,
                status=MemberStatus.active,
                branch_id=branch.id,
                team_id=team.id if team else None,
                join_date=date.today() - timedelta(days=200),
                last_active_at=datetime.now(timezone.utc),
                created_by=user.id,
            )
        )
        print(f"已创建演示会员：{username} / {DEMO_PASSWORD}（{full_name}）")
    db.commit()


def create_demo_activity(db) -> None:
    """创建一条已发布的演示活动，便于会员端报名联调。"""
    exists = db.query(Activity).filter(Activity.title == "Weekend Demo Round").first()
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
        title="Weekend Demo Round",
        description=(
            "Demo activity: members can register, bring family, and check in "
            "on-site via QR code."
        ),
        activity_type=ActivityType.weekly_round,
        status=ActivityStatus.published,
        branch_id=branch.id,
        course_name="Auckland Fairways Golf Club",
        start_at=datetime.now(timezone.utc) + timedelta(days=3),
        max_participants=20,
        max_family_slots=2,
        family_allowed=True,
        simple_scoring_enabled=True,
    )
    db.add(act)
    db.commit()
    print("已创建演示活动：Weekend Demo Round（已发布）")


def create_demo_finance(db) -> None:
    """为演示会员创建会费流水，便于账单联调。"""
    member = db.query(Member).filter(Member.chinese_name == "Alex Chen").first()
    if not member:
        print("无演示会员，跳过财务流水")
        return
    exists = (
        db.query(FinanceLedger)
        .filter(
            FinanceLedger.member_id == member.id,
            FinanceLedger.title == "2026 Annual Dues (Unpaid)",
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
            title="2026 Annual Dues (Unpaid)",
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
            title="2025 Annual Dues (Paid)",
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
            title="Association Office Expense",
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
    member = db.query(Member).filter(Member.chinese_name == "Alex Chen").first()
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

    activity = db.query(Activity).filter(Activity.title == "Weekend Demo Round").first()
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
            body_zh="您有一笔待缴费用（年度会费：2026 Annual Dues (Unpaid)），请至「我的账单」查看。",
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
            body_zh=f"您已成功报名活动「{activity.title if activity else 'Weekend Demo Round'}」。",
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
    member = db.query(Member).filter(Member.chinese_name == "Alex Chen").first()
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
            title=f"Past Weekly Round {i + 1}",
            activity_type=ActivityType.weekly_round,
            status=ActivityStatus.closed,
            branch_id=branch.id,
            course_name="Auckland Fairways Golf Club",
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
    """让演示会员已报名「Weekend Demo Round」，会员端活动 Tab 打开即有数据。"""
    member = db.query(Member).filter(Member.chinese_name == "Alex Chen").first()
    activity = db.query(Activity).filter(Activity.title == "Weekend Demo Round").first()
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
    print("已创建演示报名样例：Alex Chen 报名「Weekend Demo Round」")


def create_demo_course(db) -> None:
    """创建一个演示球场，作为赛事 course_id 的关联目标。"""
    exists = db.query(Course).filter(Course.name_zh == "Auckland Fairways Golf Club").first()
    if exists:
        print("演示球场已存在，跳过")
        return
    db.add(
        Course(
            name_zh="Auckland Fairways Golf Club",
            name_en="Auckland Fairways Golf Club",
            address="1 Fairway Drive, Auckland",
            city="Auckland",
            contact_name="Pro Shop Reception",
            contact_phone="+6491234567",
            holes=18,
            par=72,
            rating=Decimal("72.3"),
            slope=130,
            is_active=True,
        )
    )
    db.commit()
    print("已创建演示球场：Auckland Fairways Golf Club")


def create_demo_competition(db) -> None:
    """创建一条已开放报名的演示赛事，便于会员端/管理后台联调。"""
    exists = db.query(Competition).filter(Competition.name == "Auckland Spring Open").first()
    if exists:
        print("演示赛事已存在，跳过")
        return
    branch = (
        db.query(Organization)
        .filter(Organization.level == OrgLevel.branch)
        .first()
    )
    course = db.query(Course).filter(Course.name_zh == "Auckland Fairways Golf Club").first()
    director = db.query(User).filter(User.username == "director").first()
    if not branch:
        print("无分会，跳过演示赛事")
        return
    db.add(
        Competition(
            name="Auckland Spring Open",
            description=(
                "Open-for-registration demo: try the eligibility checks "
                "(member status, outstanding dues, handicap cap)."
            ),
            competition_type=CompetitionType.official,
            level="A-Grade",
            course_id=course.id if course else None,
            branch_id=branch.id,
            start_time=datetime.now(timezone.utc) + timedelta(days=21),
            registration_deadline=datetime.now(timezone.utc) + timedelta(days=14),
            fee=50,
            max_players=40,
            max_handicap=24.0,
            status=CompetitionStatus.open,
            created_by=director.id if director else None,
        )
    )
    db.commit()
    print("已创建演示赛事：Auckland Spring Open（已开放报名，差点上限 24.0）")


def create_demo_competition_registration(db) -> None:
    """让演示会员（差点 18.0，符合上限 24.0）已报名演示赛事。"""
    member = db.query(Member).filter(Member.chinese_name == "Alex Chen").first()
    competition = db.query(Competition).filter(Competition.name == "Auckland Spring Open").first()
    if not member or not competition:
        print("缺演示会员或演示赛事，跳过赛事报名样例")
        return
    exists = (
        db.query(CompetitionRegistration)
        .filter(
            CompetitionRegistration.competition_id == competition.id,
            CompetitionRegistration.member_id == member.id,
        )
        .first()
    )
    if exists:
        print("演示赛事报名样例已存在，跳过")
        return
    db.add(
        CompetitionRegistration(
            competition_id=competition.id,
            member_id=member.id,
            user_id=member.user_id,
            team_id=member.team_id,
            payment_status=CompetitionRegPaymentStatus.unpaid,
            approval_status=CompetitionRegApprovalStatus.pending,
            created_by=member.user_id,
        )
    )
    db.commit()
    print("已创建演示赛事报名样例：Alex Chen 报名「Auckland Spring Open」（待审核）")


def create_demo_groups(db) -> None:
    """审核通过演示报名并生成分组，便于两端联调 Phase 9 分组页面。"""
    competition = db.query(Competition).filter(Competition.name == "Auckland Spring Open").first()
    if not competition:
        print("无演示赛事，跳过分组样例")
        return
    existing = (
        db.query(CompetitionGroup)
        .filter(
            CompetitionGroup.competition_id == competition.id,
            CompetitionGroup.is_deleted.is_(False),
        )
        .first()
    )
    if existing:
        print("演示分组已存在，跳过")
        return

    regs = (
        db.query(CompetitionRegistration)
        .filter(
            CompetitionRegistration.competition_id == competition.id,
            CompetitionRegistration.is_deleted.is_(False),
        )
        .all()
    )
    if not regs:
        print("无赛事报名，跳过分组样例")
        return
    for reg in regs:
        if reg.approval_status != CompetitionRegApprovalStatus.approved:
            reg.approval_status = CompetitionRegApprovalStatus.approved
    db.commit()

    approved = (
        db.query(CompetitionRegistration, Member)
        .join(Member, Member.id == CompetitionRegistration.member_id)
        .filter(
            CompetitionRegistration.competition_id == competition.id,
            CompetitionRegistration.approval_status == CompetitionRegApprovalStatus.approved,
            CompetitionRegistration.is_deleted.is_(False),
        )
        .all()
    )
    players = [
        GroupingPlayer(
            member_id=reg.member_id,
            handicap=member.handicap,
            team_id=reg.team_id,
            registration_id=reg.id,
        )
        for reg, member in approved
    ]
    grouped = generate_groups(players, group_size=4)

    director = db.query(User).filter(User.username == "director").first()
    creator = director.id if director else None
    for gi, group_players in enumerate(grouped):
        group = CompetitionGroup(
            competition_id=competition.id,
            group_number=gi + 1,
            starting_hole=1,
            status=GroupStatus.scheduled,
            created_by=creator,
        )
        db.add(group)
        db.flush()
        for oi, gp in enumerate(group_players):
            db.add(
                CompetitionGroupPlayer(
                    competition_id=competition.id,
                    group_id=group.id,
                    member_id=gp.member_id,
                    registration_id=gp.registration_id,
                    order_number=oi + 1,
                    handicap=gp.handicap,
                    team_id=gp.team_id,
                    created_by=creator,
                )
            )
    db.commit()
    print(f"已创建演示分组：{len(grouped)} 组（已同步审核通过演示报名）")


def _hole_values_for_total(total: int) -> list[int]:
    """把 18 洞成绩拆成总杆为 total 的一组合理数值（每洞 4 或 5 杆为主）。"""
    base, remainder = divmod(total, 18)
    return [base + 1 if i < remainder else base for i in range(18)]


def create_demo_completed_competition(db) -> None:
    """创建一场已完结的演示赛事：报名→分组→计分→审核→排名全部走完，
    确保线上演示时 Scoring/Review/Ranking 模块不是空的。"""
    name = "Auckland Club Championship 2025"
    exists = db.query(Competition).filter(Competition.name == name).first()
    if exists:
        print("演示完结赛事已存在，跳过")
        return

    branch = (
        db.query(Organization)
        .filter(Organization.level == OrgLevel.branch)
        .first()
    )
    course = db.query(Course).filter(Course.name_zh == "Auckland Fairways Golf Club").first()
    director = db.query(User).filter(User.username == "director").first()
    if not branch or not director:
        print("缺分会或赛事总监账号，跳过演示完结赛事")
        return

    members_by_name = {
        m.chinese_name: m
        for m in db.query(Member)
        .filter(
            Member.chinese_name.in_(
                ["Alex Chen"] + [row[1] for row in _EXTRA_MEMBERS]
            )
        )
        .all()
    }
    target_by_name = {"Alex Chen": 88}
    target_by_name.update({row[1]: row[4] for row in _EXTRA_MEMBERS})
    if len(members_by_name) < 4:
        print("演示会员不足 4 人，跳过演示完结赛事")
        return

    creator = director.id
    start_time = datetime.now(timezone.utc) - timedelta(days=45)

    competition = Competition(
        name=name,
        description=(
            "Completed-tournament demo: grouping, 18-hole scoring, "
            "peer/admin review, and a published individual + team ranking."
        ),
        competition_type=CompetitionType.official,
        level="Championship",
        course_id=course.id if course else None,
        branch_id=branch.id,
        start_time=start_time,
        registration_deadline=start_time - timedelta(days=7),
        fee=60,
        max_players=4,
        max_handicap=Decimal("30.0"),
        status=CompetitionStatus.open,
        created_by=creator,
    )
    db.add(competition)
    db.flush()

    registrations: dict[int, CompetitionRegistration] = {}
    for full_name, member in members_by_name.items():
        reg = CompetitionRegistration(
            competition_id=competition.id,
            member_id=member.id,
            user_id=member.user_id,
            team_id=member.team_id,
            payment_status=CompetitionRegPaymentStatus.paid,
            approval_status=CompetitionRegApprovalStatus.approved,
            created_by=creator,
        )
        db.add(reg)
        db.flush()
        registrations[member.id] = reg
    db.commit()

    players = [
        GroupingPlayer(
            member_id=member.id,
            handicap=member.handicap,
            team_id=member.team_id,
            registration_id=registrations[member.id].id,
        )
        for member in members_by_name.values()
    ]
    grouped = generate_groups(players, group_size=4)

    team_by_member: dict[int, int | None] = {}
    cards: list[ScoreCard] = []
    for gi, group_players in enumerate(grouped):
        group = CompetitionGroup(
            competition_id=competition.id,
            group_number=gi + 1,
            starting_hole=1,
            status=GroupStatus.completed,
            created_by=creator,
        )
        db.add(group)
        db.flush()
        for oi, gp in enumerate(group_players):
            db.add(
                CompetitionGroupPlayer(
                    competition_id=competition.id,
                    group_id=group.id,
                    member_id=gp.member_id,
                    registration_id=gp.registration_id,
                    order_number=oi + 1,
                    handicap=gp.handicap,
                    team_id=gp.team_id,
                    created_by=creator,
                )
            )
            team_by_member[gp.member_id] = gp.team_id

            member = next(m for m in members_by_name.values() if m.id == gp.member_id)
            target = target_by_name[member.chinese_name]
            card = ScoreCard(
                competition_id=competition.id,
                member_id=member.id,
                group_id=group.id,
                handicap_snapshot=gp.handicap,
                status=ScoreCardStatus.approved,
                created_by=creator,
            )
            for hole_number, strokes in enumerate(_hole_values_for_total(target), start=1):
                setattr(card, f"hole{hole_number}", strokes)
            recompute_scores(card)
            db.add(card)
            db.flush()
            db.add(
                ScoreReview(
                    score_id=card.id,
                    reviewer_id=director.id,
                    status=ScoreReviewStatus.approved,
                    comment="Reviewed and approved.",
                    created_by=creator,
                )
            )
            cards.append(card)
    db.commit()

    individual_rows = compute_individual_rankings(cards)
    cards_with_team = [
        (card, team_by_member[card.member_id])
        for card in cards
        if team_by_member.get(card.member_id) is not None
    ]
    team_rows = compute_team_rankings(cards_with_team)
    for row in individual_rows + team_rows:
        db.add(
            Ranking(
                competition_id=competition.id,
                scope=row.scope,
                member_id=row.member_id,
                team_id=row.team_id,
                rank=row.rank,
                score=row.score,
                award=row.award,
                created_by=creator,
            )
        )
    competition.status = CompetitionStatus.completed
    competition.updated_by = creator
    db.commit()
    print(f"已创建演示完结赛事：{name}（{len(cards)} 张计分卡，已发布个人/球队排名）")


def create_demo_handicap_history(db) -> None:
    """为 Alex Chen 补一条差点变更历史，让 Handicap 仪表盘有真实趋势可看。"""
    member = db.query(Member).filter(Member.chinese_name == "Alex Chen").first()
    if not member:
        print("无演示会员，跳过差点历史样例")
        return
    exists = (
        db.query(HandicapHistory)
        .filter(HandicapHistory.member_id == member.id, HandicapHistory.is_deleted.is_(False))
        .first()
    )
    if exists:
        print("演示差点历史已存在，跳过")
        return

    admin = (
        db.query(User)
        .filter(User.username == settings.first_superuser_username)
        .first()
    )
    creator = admin.id if admin else None

    db.add(
        HandicapHistory(
            member_id=member.id,
            date=date.today() - timedelta(days=30),
            old_handicap=Decimal("20.0"),
            new_handicap=Decimal("18.0"),
            source=HandicapSource.manual,
            remark="Post-season handicap review",
            created_by=creator,
        )
    )
    db.commit()
    print("已创建演示差点历史：Alex Chen 20.0 → 18.0")


def create_demo_sponsor(db) -> None:
    """创建一个演示赞助商 + 合同，关联到已完结赛事，便于赞助商 CRM 模块展示。"""
    exists = db.query(Sponsor).filter(Sponsor.company_name == "Pacific Rim Motors").first()
    if exists:
        print("演示赞助商已存在，跳过")
        return

    admin = (
        db.query(User)
        .filter(User.username == settings.first_superuser_username)
        .first()
    )
    creator = admin.id if admin else None
    competition = (
        db.query(Competition)
        .filter(Competition.name == "Auckland Club Championship 2025")
        .first()
    )

    sponsor = Sponsor(
        company_name="Pacific Rim Motors",
        industry="Automotive",
        contact_name="Sam Turner",
        phone="+6499876543",
        email="sponsorship@pacificrimmotors.example",
        website="https://pacificrimmotors.example",
        level="Gold",
        is_active=True,
        created_by=creator,
    )
    db.add(sponsor)
    db.flush()
    db.add(
        SponsorContract(
            sponsor_id=sponsor.id,
            competition_id=competition.id if competition else None,
            amount=Decimal("5000.00"),
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() + timedelta(days=305),
            benefit="Clubhouse banner placement and prize table sponsorship",
            created_by=creator,
        )
    )
    db.commit()
    print("已创建演示赞助商：Pacific Rim Motors（金牌赞助，关联 Club Championship 2025）")


def seed_all() -> None:
    create_first_superuser()
    db = SessionLocal()
    try:
        create_headquarters(db)
        create_demo_world(db)
        create_demo_team_b(db)
        create_demo_member(db)
        create_demo_extra_members(db)
        create_demo_activity(db)
        create_demo_finance(db)
        create_demo_messages(db)
        create_demo_attendance(db)
        create_demo_registration(db)
        create_demo_course(db)
        create_demo_competition(db)
        create_demo_competition_registration(db)
        create_demo_groups(db)
        create_demo_completed_competition(db)
        create_demo_handicap_history(db)
        create_demo_sponsor(db)
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()
