"""运营数据分析：会员/活动/比赛/财务四大板块的只读聚合查询。"""
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.activity import Activity, ActivityRegistration, RegistrantType, RegistrationStatus
from app.models.competition import Competition, CompetitionRegApprovalStatus, CompetitionRegistration
from app.models.finance import FinanceLedger, LedgerDirection, LedgerStatus
from app.models.handicap import HandicapHistory
from app.models.member import Member, MemberStatus
from app.models.scorecard import ScoreCard, ScoreCardStatus
from app.models.sponsor import SponsorContract
from app.models.team import Team

_ACTIVITY_COUNTED_STATUSES = (
    RegistrationStatus.registered,
    RegistrationStatus.checked_in,
    RegistrationStatus.absent,
)


def member_stats(db: Session, branch_id: int | None) -> dict:
    q = db.query(Member).filter(Member.is_deleted.is_(False))
    if branch_id is not None:
        q = q.filter(Member.branch_id == branch_id)
    total = q.count()
    cutoff = date.today() - timedelta(days=30)
    new_last_30d = q.filter(Member.join_date >= cutoff).count()
    active = q.filter(Member.status == MemberStatus.active).count()
    sleeping = q.filter(Member.status == MemberStatus.sleeping).count()

    team_q = db.query(Team).filter(Team.is_deleted.is_(False))
    if branch_id is not None:
        team_q = team_q.filter(Team.branch_id == branch_id)
    team_count = team_q.count()

    return {
        "total": total,
        "new_last_30d": new_last_30d,
        "active": active,
        "sleeping": sleeping,
        "team_count": team_count,
    }


def _activity_member_count(db: Session, activity_id: int) -> int:
    return (
        db.query(ActivityRegistration)
        .filter(
            ActivityRegistration.activity_id == activity_id,
            ActivityRegistration.registrant_type == RegistrantType.member,
            ActivityRegistration.status.in_(_ACTIVITY_COUNTED_STATUSES),
            ActivityRegistration.is_deleted.is_(False),
        )
        .count()
    )


def _active_trend(db: Session, branch_id: int | None) -> list[dict]:
    """近 6 个月，每月按 check-in 时间统计的去重活跃会员数。"""
    first_of_this_month = date.today().replace(day=1)
    month_starts: list[date] = []
    cursor = first_of_this_month
    for _ in range(6):
        month_starts.append(cursor)
        year = cursor.year - 1 if cursor.month == 1 else cursor.year
        month = 12 if cursor.month == 1 else cursor.month - 1
        cursor = date(year, month, 1)
    month_starts.reverse()

    results = []
    for start in month_starts:
        end = date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
        q = (
            db.query(ActivityRegistration.member_id)
            .join(Activity, Activity.id == ActivityRegistration.activity_id)
            .filter(
                ActivityRegistration.status == RegistrationStatus.checked_in,
                ActivityRegistration.checked_in_at >= start,
                ActivityRegistration.checked_in_at < end,
                ActivityRegistration.is_deleted.is_(False),
            )
        )
        if branch_id is not None:
            q = q.filter(Activity.branch_id == branch_id)
        count = q.distinct().count()
        results.append({"month": start.strftime("%Y-%m"), "active_member_count": count})
    return results


def activity_stats(db: Session, branch_id: int | None) -> dict:
    q = db.query(Activity).filter(Activity.is_deleted.is_(False))
    if branch_id is not None:
        q = q.filter(Activity.branch_id == branch_id)
    activities = q.all()

    if not activities:
        return {
            "total": 0,
            "avg_participants": 0.0,
            "most_attended": None,
            "active_trend": _active_trend(db, branch_id),
        }

    counts = [(a, _activity_member_count(db, a.id)) for a in activities]
    avg_participants = round(sum(c for _, c in counts) / len(counts), 1)
    top_activity, top_count = max(counts, key=lambda pair: pair[1])

    return {
        "total": len(activities),
        "avg_participants": avg_participants,
        "most_attended": {"id": top_activity.id, "title": top_activity.title, "count": top_count},
        "active_trend": _active_trend(db, branch_id),
    }


def _handicap_change(db: Session, branch_id: int | None) -> float | None:
    cutoff = date.today() - timedelta(days=90)
    q = (
        db.query(HandicapHistory)
        .join(Member, Member.id == HandicapHistory.member_id)
        .filter(
            HandicapHistory.date >= cutoff,
            HandicapHistory.is_deleted.is_(False),
            Member.is_deleted.is_(False),
        )
    )
    if branch_id is not None:
        q = q.filter(Member.branch_id == branch_id)
    diffs = [
        float(row.new_handicap) - float(row.old_handicap)
        for row in q.all()
        if row.old_handicap is not None
    ]
    if not diffs:
        return None
    return round(sum(diffs) / len(diffs), 2)


def competition_stats(db: Session, branch_id: int | None) -> dict:
    comp_q = db.query(Competition).filter(Competition.is_deleted.is_(False))
    if branch_id is not None:
        comp_q = comp_q.filter(Competition.branch_id == branch_id)
    comp_ids = [c.id for c in comp_q.all()]

    if not comp_ids:
        return {
            "total": 0,
            "total_participants": 0,
            "avg_net_score": None,
            "handicap_change": _handicap_change(db, branch_id),
        }

    total_participants = (
        db.query(CompetitionRegistration)
        .filter(
            CompetitionRegistration.competition_id.in_(comp_ids),
            CompetitionRegistration.approval_status == CompetitionRegApprovalStatus.approved,
            CompetitionRegistration.is_deleted.is_(False),
        )
        .count()
    )

    cards = (
        db.query(ScoreCard)
        .filter(
            ScoreCard.competition_id.in_(comp_ids),
            ScoreCard.status == ScoreCardStatus.approved,
            ScoreCard.is_deleted.is_(False),
        )
        .all()
    )
    avg_net_score = (
        round(float(sum(c.net_score for c in cards)) / len(cards), 1) if cards else None
    )

    return {
        "total": len(comp_ids),
        "total_participants": total_participants,
        "avg_net_score": avg_net_score,
        "handicap_change": _handicap_change(db, branch_id),
    }


def finance_stats(db: Session, branch_id: int | None) -> dict:
    base = db.query(FinanceLedger).filter(
        FinanceLedger.status == LedgerStatus.confirmed,
        FinanceLedger.is_deleted.is_(False),
    )
    if branch_id is not None:
        base = base.filter(FinanceLedger.branch_id == branch_id)

    income = (
        base.filter(FinanceLedger.direction == LedgerDirection.income)
        .with_entities(func.sum(FinanceLedger.amount))
        .scalar()
        or 0
    )
    expense = (
        base.filter(FinanceLedger.direction == LedgerDirection.expense)
        .with_entities(func.sum(FinanceLedger.amount))
        .scalar()
        or 0
    )

    today = date.today()
    sponsorship_total = (
        db.query(SponsorContract)
        .filter(
            SponsorContract.is_deleted.is_(False),
            (SponsorContract.end_date.is_(None)) | (SponsorContract.end_date >= today),
        )
        .with_entities(func.sum(SponsorContract.amount))
        .scalar()
        or 0
    )

    return {
        "income": income,
        "expense": expense,
        "profit": income - expense,
        "sponsorship_total": sponsorship_total,
    }
