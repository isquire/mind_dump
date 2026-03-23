"""Tasks: CRUD, pin/unpin One Thing, status updates."""
import bleach
from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from models import db, Task, Project, MindDump
from forms.task import TaskForm

tasks_bp = Blueprint('tasks', __name__, url_prefix='/tasks')

# Tags and attributes allowed in Quill rich-text notes
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's', 'h1', 'h2', 'h3',
    'ul', 'ol', 'li', 'blockquote', 'pre', 'code', 'a', 'span',
]
ALLOWED_ATTRS = {'a': ['href', 'rel', 'target'], 'span': ['class'], '*': ['class']}


def _sanitize_notes(html: str) -> str:
    """Strip disallowed HTML tags from Quill output."""
    return bleach.clean(html or '', tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)


def _populate_project_choices(form):
    """Fill the project_id select with a blank 'no project' option first."""
    projects = Project.query.order_by(Project.title).all()
    form.project_id.choices = [('', '— No project (Quick Task) —')] + [(p.id, p.title) for p in projects]
    return projects


@tasks_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = TaskForm()
    projects = _populate_project_choices(form)

    from_dump_id = request.args.get('from_dump', type=int)
    preselect_project = request.args.get('project_id', type=int)
    if request.method == 'GET':
        prefill = request.args.get('prefill', '')
        prefill_category = request.args.get('prefill_category', '')
        if prefill:
            form.title.data = prefill[:200]
        if preselect_project:
            form.project_id.data = preselect_project
        if prefill_category in ('work', 'personal'):
            form.category.data = prefill_category

    if form.validate_on_submit():
        link = (form.external_link.data or '').strip()
        cat = form.category.data if form.category.data in ('work', 'personal') else 'work'
        task = Task(
            project_id=form.project_id.data,
            title=form.title.data.strip(),
            notes=_sanitize_notes(form.notes.data),
            status=form.status.data or 'Not Started',
            due_date=form.due_date.data or None,
            external_link=link or None,
            category=cat,
        )
        db.session.add(task)
        db.session.flush()

        if from_dump_id:
            entry = db.session.get(MindDump, from_dump_id)
            if entry:
                entry.status = 'Assigned'
                entry.linked_task_id = task.id

        db.session.commit()
        flash(f'Task "{task.title}" created!', 'success')
        if task.project_id:
            return redirect(url_for('projects.detail', project_id=task.project_id))
        return redirect(url_for('dashboard.index'))

    return render_template('tasks/form.html', form=form, task=None)


@tasks_bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(task_id):
    task = db.get_or_404(Task, task_id)
    form = TaskForm(obj=task)
    _populate_project_choices(form)
    if request.method == 'GET':
        form.project_id.data = task.project_id if task.project_id else ''

    if form.validate_on_submit():
        link = (form.external_link.data or '').strip()
        task.project_id = form.project_id.data
        task.title = form.title.data.strip()
        task.notes = _sanitize_notes(form.notes.data)
        task.status = form.status.data or 'Not Started'
        task.due_date = form.due_date.data or None
        task.external_link = link or None
        if form.category.data in ('work', 'personal'):
            task.category = form.category.data
        # Mark completed_at when status changes to Done
        if task.status == 'Done' and not task.completed_at:
            task.completed_at = datetime.now(timezone.utc)
        elif task.status != 'Done':
            task.completed_at = None
        db.session.commit()
        flash(f'Task "{task.title}" updated.', 'success')
        if task.project_id:
            return redirect(url_for('projects.detail', project_id=task.project_id))
        return redirect(url_for('dashboard.index'))

    return render_template('tasks/form.html', form=form, task=task)


@tasks_bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
def delete(task_id):
    task = db.get_or_404(Task, task_id)
    project_id = task.project_id
    title = task.title
    db.session.delete(task)
    db.session.commit()
    flash(f'Task "{title}" deleted.', 'success')
    if project_id:
        return redirect(url_for('projects.detail', project_id=project_id))
    return redirect(url_for('dashboard.index'))


@tasks_bp.route('/<int:task_id>/pin', methods=['POST'])
@login_required
def pin(task_id):
    """Pin as My One Thing — unpins any previously pinned task first."""
    # Unpin all other tasks
    Task.query.filter(Task.is_pinned == True, Task.id != task_id).update(
        {'is_pinned': False}, synchronize_session=False
    )
    task = db.get_or_404(Task, task_id)
    task.is_pinned = True
    db.session.commit()
    flash(f'"{task.title}" is your One Thing.', 'success')
    return redirect(request.referrer or url_for('dashboard.index'))


@tasks_bp.route('/<int:task_id>/unpin', methods=['POST'])
@login_required
def unpin(task_id):
    task = db.get_or_404(Task, task_id)
    task.is_pinned = False
    db.session.commit()
    flash('One Thing cleared.', 'info')
    return redirect(request.referrer or url_for('dashboard.index'))


@tasks_bp.route('/<int:task_id>/complete', methods=['POST'])
@login_required
def complete(task_id):
    task = db.get_or_404(Task, task_id)
    task.status = 'Done'
    task.completed_at = datetime.now(timezone.utc)
    task.is_pinned = False
    db.session.commit()
    flash(f'"{task.title}" done! Great work.', 'success')
    return redirect(request.referrer or url_for('dashboard.index'))
