"""Mind Dump: quick-capture list with one-click triage actions."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from models import db, MindDump, Task, Project, BigIdea
from forms.mind_dump import QuickCaptureForm, EditMindDumpForm
from utils import default_category

mind_dump_bp = Blueprint('mind_dump', __name__, url_prefix='/mind-dump')


@mind_dump_bp.route('/')
@login_required
def index():
    entries = MindDump.query.order_by(MindDump.created_at.desc()).all()
    form = QuickCaptureForm()
    return render_template(
        'mind_dump/index.html',
        entries=entries,
        form=form,
        default_category=default_category(),
    )


@mind_dump_bp.route('/capture', methods=['POST'])
@login_required
def capture():
    form = QuickCaptureForm()
    if form.validate_on_submit():
        cat = form.category.data or ''
        if cat not in ('work', 'personal'):
            cat = default_category()
        entry = MindDump(content=form.content.data.strip(), category=cat)
        db.session.add(entry)
        db.session.commit()
        flash('Captured!', 'success')
    return redirect(url_for('mind_dump.index'))


@mind_dump_bp.route('/<int:entry_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(entry_id):
    entry = db.get_or_404(MindDump, entry_id)
    form = EditMindDumpForm(obj=entry)
    if request.method == 'GET':
        form.category.data = entry.category
    if form.validate_on_submit():
        entry.content = form.content.data.strip()
        cat = form.category.data
        if cat in ('work', 'personal'):
            entry.category = cat
        db.session.commit()
        flash('Entry updated.', 'success')
        return redirect(url_for('mind_dump.index'))
    return render_template('mind_dump/edit.html', form=form, entry=entry)


@mind_dump_bp.route('/<int:entry_id>/someday', methods=['POST'])
@login_required
def mark_someday(entry_id):
    entry = db.get_or_404(MindDump, entry_id)
    entry.status = 'Someday'
    db.session.commit()
    flash('Moved to Someday/Maybe.', 'info')
    return redirect(url_for('mind_dump.index'))


@mind_dump_bp.route('/<int:entry_id>/delete', methods=['POST'])
@login_required
def delete(entry_id):
    entry = db.get_or_404(MindDump, entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash('Entry deleted.', 'success')
    return redirect(url_for('mind_dump.index'))


@mind_dump_bp.route('/<int:entry_id>/promote-task')
@login_required
def promote_task(entry_id):
    """Redirect to task creation form pre-filled with mind dump content and category."""
    entry = db.get_or_404(MindDump, entry_id)
    return redirect(url_for(
        'tasks.new',
        from_dump=entry_id,
        prefill=entry.content,
        prefill_category=entry.category,
    ))


@mind_dump_bp.route('/<int:entry_id>/promote-project')
@login_required
def promote_project(entry_id):
    """Redirect to project creation form pre-filled with mind dump content and category."""
    entry = db.get_or_404(MindDump, entry_id)
    return redirect(url_for(
        'projects.new',
        from_dump=entry_id,
        prefill=entry.content,
        prefill_category=entry.category,
    ))


@mind_dump_bp.route('/<int:entry_id>/promote-big-idea')
@login_required
def promote_big_idea(entry_id):
    """Redirect to big idea creation form pre-filled with mind dump content and category."""
    entry = db.get_or_404(MindDump, entry_id)
    return redirect(url_for(
        'big_ideas.new',
        from_dump=entry_id,
        prefill=entry.content,
        prefill_category=entry.category,
    ))
