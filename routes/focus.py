"""Focus Mode: distraction-free single-task view."""
from datetime import datetime, timezone, date, timedelta

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required

from models import db, Task

focus_bp = Blueprint('focus', __name__)


@focus_bp.route('/focus/<int:task_id>')
@login_required
def view(task_id):
    task = db.get_or_404(Task, task_id)
    return render_template('focus.html', task=task)


@focus_bp.route('/focus/<int:task_id>/complete', methods=['POST'])
@login_required
def complete(task_id):
    task = db.get_or_404(Task, task_id)
    task.status = 'Done'
    task.completed_at = datetime.now(timezone.utc)
    task.is_pinned = False
    db.session.commit()
    # Return to focus view so the completion animation plays, then user navigates away
    return render_template('focus.html', task=task, just_completed=True)


@focus_bp.route('/focus/<int:task_id>/snooze', methods=['POST'])
@login_required
def snooze(task_id):
    task = db.get_or_404(Task, task_id)
    # Always snooze to tomorrow regardless of current due date
    task.due_date = date.today() + timedelta(days=1)
    db.session.commit()
    flash(f'"{task.title}" snoozed to tomorrow.', 'info')
    return redirect(url_for('dashboard.index'))
