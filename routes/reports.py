"""Reports: cross-entity insights and productivity summary."""
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func

from models import db, Task, BigIdea, MindDump
from utils import apply_category_filter

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/reports')
@login_required
def index():
    view = current_user.view_preference or 'all'
    today = date.today()

    # Base task query filtered by view preference
    base = Task.query
    if view in ('work', 'personal'):
        base = base.filter(Task.category == view)

    # ── KPI counts ──────────────────────────────────────────────────────────
    total_tasks   = base.count()
    done_tasks    = base.filter(Task.status == 'Done').count()
    active_tasks  = base.filter(Task.status != 'Done').count()
    not_started   = base.filter(Task.status == 'Not Started').count()
    in_progress   = base.filter(Task.status == 'In Progress').count()
    blocked_tasks = base.filter(Task.status == 'Blocked').count()
    overdue_tasks = base.filter(
        Task.status != 'Done',
        Task.due_date < today,
        Task.due_date.isnot(None),
    ).count()

    # ── Last 30 days completions ─────────────────────────────────────────────
    thirty_days_ago = datetime.combine(
        today - timedelta(days=29), datetime.min.time()
    ).replace(tzinfo=timezone.utc)
    recent_rows = (
        Task.query
        .filter(Task.completed_at >= thirty_days_ago)
        .with_entities(Task.completed_at)
        .all()
    )
    daily_counts = defaultdict(int)
    for (completed_at,) in recent_rows:
        daily_counts[completed_at.date()] += 1

    days_30 = [
        (today - timedelta(days=i), daily_counts.get(today - timedelta(days=i), 0))
        for i in range(29, -1, -1)
    ]
    max_day_count = max((c for _, c in days_30), default=0) or 1
    recent_total  = sum(c for _, c in days_30)
    busiest       = max(days_30, key=lambda x: x[1])

    # ── Streak ────────────────────────────────────────────────────────────────
    all_dates = {
        row[0].date()
        for row in Task.query.filter(Task.completed_at.isnot(None))
        .with_entities(Task.completed_at).all()
    }
    streak, check = 0, today
    while check in all_dates:
        streak += 1
        check -= timedelta(days=1)

    # ── Big Ideas health (always show all, unfiltered) ───────────────────────
    big_ideas = BigIdea.query.order_by(BigIdea.title).all()
    # Compute overdue task count per big idea across all its projects
    idea_overdue = {}
    for idea in big_ideas:
        count = 0
        for project in idea.projects:
            count += sum(1 for t in project.tasks if t.is_overdue)
        idea_overdue[idea.id] = count

    # ── Mind Dump counts ─────────────────────────────────────────────────────
    dump_unorganized = MindDump.query.filter_by(status='Unorganized').count()
    dump_someday     = MindDump.query.filter_by(status='Someday').count()
    dump_assigned    = MindDump.query.filter_by(status='Assigned').count()
    dump_total       = dump_unorganized + dump_someday + dump_assigned

    # ── Estimated time remaining ─────────────────────────────────────────────
    est_q = db.session.query(func.sum(Task.estimated_minutes)).filter(
        Task.status != 'Done', Task.estimated_minutes.isnot(None)
    )
    if view in ('work', 'personal'):
        est_q = est_q.filter(Task.category == view)
    estimated_minutes_total = est_q.scalar() or 0

    tasks_no_estimate = base.filter(
        Task.status != 'Done', Task.estimated_minutes.is_(None)
    ).count()

    return render_template(
        'reports.html',
        view=view,
        today=today,
        # KPIs
        total_tasks=total_tasks,
        done_tasks=done_tasks,
        active_tasks=active_tasks,
        not_started=not_started,
        in_progress=in_progress,
        blocked_tasks=blocked_tasks,
        overdue_tasks=overdue_tasks,
        # 30-day chart
        days_30=days_30,
        max_day_count=max_day_count,
        recent_total=recent_total,
        busiest=busiest,
        streak=streak,
        # Big Ideas
        big_ideas=big_ideas,
        idea_overdue=idea_overdue,
        # Mind Dump
        dump_unorganized=dump_unorganized,
        dump_someday=dump_someday,
        dump_assigned=dump_assigned,
        dump_total=dump_total,
        # Time estimates
        estimated_minutes_total=estimated_minutes_total,
        tasks_no_estimate=tasks_no_estimate,
    )
