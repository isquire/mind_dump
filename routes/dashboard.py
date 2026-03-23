"""Dashboard: quick capture, One Thing, today/week tasks, overdue tasks."""
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from models import db, Task, MindDump
from forms.mind_dump import QuickCaptureForm

dashboard_bp = Blueprint('dashboard', __name__)

VALID_VIEWS = ('work', 'all', 'personal')


def _default_category() -> str:
    """Return 'work' during 9 AM–5 PM Mon–Fri, 'personal' otherwise."""
    now = datetime.now()
    if now.weekday() < 5 and 9 <= now.hour < 17:
        return 'work'
    return 'personal'


def _apply_category_filter(query, view):
    if view in ('work', 'personal'):
        return query.filter(Task.category == view)
    return query  # 'all' — no filter


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
    one_thing_q = _apply_category_filter(one_thing_q, view)
    one_thing = one_thing_q.first()

    tasks_today = (
        _apply_category_filter(
            Task.query.filter(Task.due_date == today, Task.status != 'Done'), view
        )
        .order_by(Task.created_at)
        .all()
    )
    tasks_week = (
        _apply_category_filter(
            Task.query.filter(Task.due_date > today, Task.due_date <= week_end, Task.status != 'Done'),
            view,
        )
        .order_by(Task.due_date)
        .all()
    )
    tasks_overdue = (
        _apply_category_filter(
            Task.query.filter(Task.due_date < today, Task.status != 'Done'), view
        )
        .order_by(Task.due_date)
        .all()
    )

    # Quick tasks: no project, no due date, not done
    tasks_quick = (
        _apply_category_filter(
            Task.query.filter(Task.project_id.is_(None), Task.due_date.is_(None), Task.status != 'Done'),
            view,
        )
        .order_by(Task.created_at.desc())
        .all()
    )

    # Weekly completion progress (scoped to view)
    week_q_base = Task.query.filter(
        Task.due_date >= week_start,
        Task.due_date <= week_progress_end,
    )
    if view in ('work', 'personal'):
        week_q_base = week_q_base.filter(Task.category == view)
    week_total = week_q_base.count()
    week_done = week_q_base.filter(Task.status == 'Done').count()
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
    )


@dashboard_bp.route('/set-view', methods=['POST'])
@login_required
def set_view():
    view = request.form.get('view', 'all')
    if view in VALID_VIEWS:
        current_user.view_preference = view
        db.session.commit()
    return redirect(request.referrer or url_for('dashboard.index'))


@dashboard_bp.route('/quick-capture', methods=['POST'])
@login_required
def quick_capture():
    form = QuickCaptureForm()
    if form.validate_on_submit():
        # Capture inherits the active view; 'all' falls back to time-based default
        view = current_user.view_preference or 'all'
        cat = view if view in ('work', 'personal') else _default_category()
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
