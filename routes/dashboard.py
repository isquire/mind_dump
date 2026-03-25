"""Dashboard: quick capture, One Thing, today/week tasks, overdue tasks."""
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from models import db, Task, MindDump
from forms.mind_dump import QuickCaptureForm
from utils import VALID_VIEWS, default_category, apply_category_filter, safe_referrer_redirect

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    view = current_user.view_preference or 'all'
    today = date.today()
    week_end = today + timedelta(days=7)
    # Monday of current week for progress calculation
    week_start = today - timedelta(days=today.weekday())
    week_progress_end = week_start + timedelta(days=7)

    one_thing_q = Task.query.filter_by(is_pinned=True)
    one_thing_q = apply_category_filter(one_thing_q, view)
    one_thing = one_thing_q.first()

    tasks_today = (
        apply_category_filter(
            Task.query.filter(Task.due_date == today, Task.status != 'Done'), view
        )
        .order_by(Task.created_at)
        .all()
    )
    tasks_week = (
        apply_category_filter(
            Task.query.filter(Task.due_date > today, Task.due_date <= week_end, Task.status != 'Done'),
            view,
        )
        .order_by(Task.due_date)
        .all()
    )
    tasks_overdue = (
        apply_category_filter(
            Task.query.filter(Task.due_date < today, Task.status != 'Done'), view
        )
        .order_by(Task.due_date)
        .all()
    )

    # Quick tasks: no project, no due date, not done
    tasks_quick = (
        apply_category_filter(
            Task.query.filter(Task.project_id.is_(None), Task.due_date.is_(None), Task.status != 'Done'),
            view,
        )
        .order_by(Task.created_at.desc())
        .all()
    )

    # ── Streak: consecutive days with ≥1 completed task ────────────────────
    all_completed = Task.query.filter(Task.completed_at.isnot(None)).with_entities(Task.completed_at).all()
    completed_dates = {row[0].date() for row in all_completed}
    streak = 0
    check = date.today()
    while check in completed_dates:
        streak += 1
        check -= timedelta(days=1)

    # ── Today's completed count ─────────────────────────────────────────────
    start_of_today = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    today_done_count = Task.query.filter(Task.completed_at >= start_of_today).count()

    # ── Today's estimated minutes (not-done tasks due today with estimates) ─
    from sqlalchemy import func as sa_func
    est_result = db.session.query(sa_func.sum(Task.estimated_minutes)).filter(
        Task.due_date == today,
        Task.status != 'Done',
        Task.estimated_minutes.isnot(None),
    ).scalar()
    today_estimated_minutes = est_result or 0

    # Weekly completion progress (scoped to view) — single aggregated query
    from sqlalchemy import func, case as sa_case
    week_q = db.session.query(
        func.count(Task.id).label('total'),
        func.sum(sa_case((Task.status == 'Done', 1), else_=0)).label('done'),
    ).filter(Task.due_date >= week_start, Task.due_date <= week_progress_end)
    if view in ('work', 'personal'):
        week_q = week_q.filter(Task.category == view)
    week_result = week_q.one()
    week_total = week_result.total or 0
    week_done = week_result.done or 0
    weekly_pct = int((week_done / week_total * 100) if week_total > 0 else 0)

    form = QuickCaptureForm()

    return render_template(
        'dashboard.html',
        form=form,
        one_thing=one_thing,
        tasks_today=tasks_today,
        tasks_week=tasks_week,
        tasks_overdue=tasks_overdue,
        tasks_quick=tasks_quick,
        week_total=week_total,
        week_done=week_done,
        weekly_pct=weekly_pct,
        today=today,
        streak=streak,
        today_done_count=today_done_count,
        today_estimated_minutes=today_estimated_minutes,
    )


@dashboard_bp.route('/set-view', methods=['POST'])
@login_required
def set_view():
    view = request.form.get('view', 'all')
    if view in VALID_VIEWS:
        current_user.view_preference = view
        db.session.commit()
    return safe_referrer_redirect('dashboard.index')


@dashboard_bp.route('/quick-capture', methods=['POST'])
@login_required
def quick_capture():
    form = QuickCaptureForm()
    if form.validate_on_submit():
        # Use the category the user explicitly chose; fall back to view preference
        # or time-of-day default when neither is set.
        chosen = form.category.data
        if chosen in ('work', 'personal'):
            cat = chosen
        else:
            view = current_user.view_preference or 'all'
            cat = view if view in ('work', 'personal') else default_category()
        entry = MindDump(content=form.content.data.strip(), category=cat)
        db.session.add(entry)
        db.session.commit()
        flash('Captured!', 'success')
    else:
        flash('Could not capture — please try again.', 'warning')
    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/task/<int:task_id>/reschedule-tomorrow', methods=['POST'])
@login_required
def reschedule_tomorrow(task_id):
    task = db.get_or_404(Task, task_id)
    task.due_date = date.today() + timedelta(days=1)
    db.session.commit()
    flash(f'"{task.title}" moved to tomorrow.', 'success')
    return redirect(url_for('dashboard.index'))
