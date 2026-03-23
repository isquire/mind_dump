"""Dashboard: quick capture, One Thing, today/week tasks, overdue tasks."""
from datetime import date, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required

from models import db, Task, MindDump
from forms.mind_dump import QuickCaptureForm

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@login_required
def index():
    today = date.today()
    week_end = today + timedelta(days=7)
    # Monday of current week for progress calculation
    week_start = today - timedelta(days=today.weekday())
    week_progress_end = week_start + timedelta(days=7)

    one_thing = Task.query.filter_by(is_pinned=True).first()

    tasks_today = (
        Task.query
        .filter(Task.due_date == today, Task.status != 'Done')
        .order_by(Task.created_at)
        .all()
    )
    tasks_week = (
        Task.query
        .filter(Task.due_date > today, Task.due_date <= week_end, Task.status != 'Done')
        .order_by(Task.due_date)
        .all()
    )
    tasks_overdue = (
        Task.query
        .filter(Task.due_date < today, Task.status != 'Done')
        .order_by(Task.due_date)
        .all()
    )

    # Weekly completion progress
    week_total = Task.query.filter(
        Task.due_date >= week_start,
        Task.due_date <= week_progress_end
    ).count()
    week_done = Task.query.filter(
        Task.due_date >= week_start,
        Task.due_date <= week_progress_end,
        Task.status == 'Done'
    ).count()
    weekly_pct = int((week_done / week_total * 100) if week_total > 0 else 0)

    form = QuickCaptureForm()

    return render_template(
        'dashboard.html',
        form=form,
        one_thing=one_thing,
        tasks_today=tasks_today,
        tasks_week=tasks_week,
        tasks_overdue=tasks_overdue,
        week_total=week_total,
        week_done=week_done,
        weekly_pct=weekly_pct,
        today=today,
    )


@dashboard_bp.route('/quick-capture', methods=['POST'])
@login_required
def quick_capture():
    form = QuickCaptureForm()
    if form.validate_on_submit():
        entry = MindDump(content=form.content.data.strip())
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
