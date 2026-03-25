"""Big Ideas: CRUD for top-level goal/theme containers."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import nullslast

from models import db, BigIdea, Project, Task, MindDump
from forms.big_idea import BigIdeaForm

big_ideas_bp = Blueprint('big_ideas', __name__, url_prefix='/big-ideas')


@big_ideas_bp.route('/')
@login_required
def index():
    view = current_user.view_preference or 'all'
    q = BigIdea.query.order_by(nullslast(BigIdea.position.asc()), BigIdea.created_at.desc())
    if view in ('work', 'personal'):
        q = q.filter(BigIdea.category == view)
    ideas = q.all()
    return render_template('big_ideas/index.html', ideas=ideas)


@big_ideas_bp.route('/reorder', methods=['POST'])
@login_required
def reorder():
    data = request.get_json(silent=True) or {}
    idea_ids = data.get('idea_ids', [])
    if not isinstance(idea_ids, list):
        return {'ok': False, 'error': 'invalid'}, 400
    for pos, iid in enumerate(idea_ids):
        idea = db.session.get(BigIdea, iid)
        if idea:
            idea.position = pos
    db.session.commit()
    return {'ok': True}


@big_ideas_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = BigIdeaForm()
    # Pre-fill from Mind Dump promotion
    from_dump_id = request.args.get('from_dump', type=int)
    if request.method == 'GET':
        prefill = request.args.get('prefill', '')
        prefill_category = request.args.get('prefill_category', '')
        if prefill:
            form.title.data = prefill[:200]
        if prefill_category in ('work', 'personal'):
            form.category.data = prefill_category

    if form.validate_on_submit():
        cat = form.category.data if form.category.data in ('work', 'personal') else 'work'
        idea = BigIdea(
            title=form.title.data.strip(),
            description=(form.description.data or '').strip(),
            accent_color=form.accent_color.data or '#6366f1',
            category=cat,
        )
        db.session.add(idea)
        db.session.flush()  # get idea.id before commit

        # Mark mind dump entry as assigned if promoted
        if from_dump_id:
            entry = db.session.get(MindDump, from_dump_id)
            if entry:
                entry.status = 'Assigned'
                entry.linked_big_idea_id = idea.id

        db.session.commit()
        flash(f'Big Idea "{idea.title}" created!', 'success')
        if from_dump_id:
            return redirect(url_for('mind_dump.index'))
        return redirect(url_for('big_ideas.index'))

    return render_template('big_ideas/form.html', form=form, idea=None)


@big_ideas_bp.route('/<int:idea_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(idea_id):
    idea = db.get_or_404(BigIdea, idea_id)
    form = BigIdeaForm(obj=idea)

    if request.method == 'GET':
        form.category.data = idea.category

    if form.validate_on_submit():
        idea.title = form.title.data.strip()
        idea.description = (form.description.data or '').strip()
        idea.accent_color = form.accent_color.data or '#6366f1'
        if form.category.data in ('work', 'personal'):
            idea.category = form.category.data
        db.session.commit()
        flash(f'Big Idea "{idea.title}" updated.', 'success')
        return redirect(url_for('big_ideas.index'))

    return render_template('big_ideas/form.html', form=form, idea=idea)


@big_ideas_bp.route('/<int:idea_id>/delete', methods=['POST'])
@login_required
def delete(idea_id):
    idea = db.get_or_404(BigIdea, idea_id)
    title = idea.title
    db.session.delete(idea)
    db.session.commit()
    flash(f'Big Idea "{title}" and all its projects deleted.', 'success')
    return redirect(url_for('big_ideas.index'))


@big_ideas_bp.route('/<int:idea_id>/downgrade', methods=['GET', 'POST'])
@login_required
def downgrade(idea_id):
    """Convert a Big Idea down to a Project or standalone Task."""
    idea = db.get_or_404(BigIdea, idea_id)
    target = request.args.get('to') or request.form.get('to', '')
    if target not in ('project', 'task'):
        flash('Specify a downgrade target: project or task.', 'danger')
        return redirect(url_for('big_ideas.index'))

    other_ideas = BigIdea.query.filter(BigIdea.id != idea_id).order_by(BigIdea.title).all()
    sub_project_count = len(idea.projects)

    if request.method == 'GET':
        # Downgrade to project requires at least one other Big Idea to nest under
        if target == 'project' and not other_ideas:
            flash(
                'Create at least one other Big Idea first — '
                'a project must belong to a Big Idea.',
                'warning',
            )
            return redirect(url_for('big_ideas.index'))
        return render_template(
            'big_ideas/downgrade.html',
            idea=idea,
            target=target,
            other_ideas=other_ideas,
            sub_project_count=sub_project_count,
        )

    # POST — execute the downgrade
    reassign_to_id = request.form.get('reassign_to_id', type=int)

    # Detach sub-projects from this Big Idea before deleting it
    if sub_project_count:
        if reassign_to_id:
            Project.query.filter_by(big_idea_id=idea_id).update({'big_idea_id': reassign_to_id})
        # else: sub-projects will be cascade-deleted with the Big Idea

    if target == 'project':
        parent_id = reassign_to_id or (other_ideas[0].id if other_ideas else None)
        if not parent_id:
            flash('No Big Idea available to place the new project under.', 'warning')
            return redirect(url_for('big_ideas.index'))
        project = Project(
            big_idea_id=parent_id,
            title=idea.title,
            description=idea.description or '',
            category=idea.category,
        )
        db.session.add(project)
        db.session.flush()
        db.session.delete(idea)
        db.session.commit()
        flash(f'"{project.title}" converted to a project.', 'success')
        return redirect(url_for('projects.detail', project_id=project.id))

    # target == 'task'
    task = Task(
        title=idea.title,
        first_action=idea.description[:500] if idea.description else None,
        status='Not Started',
        category=idea.category,
    )
    db.session.add(task)
    db.session.flush()
    db.session.delete(idea)
    db.session.commit()
    flash(f'"{task.title}" converted to a standalone task.', 'success')
    return redirect(url_for('dashboard.index'))
