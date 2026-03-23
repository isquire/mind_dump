"""Projects: CRUD for projects belonging to a Big Idea."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from models import db, Project, BigIdea, MindDump
from forms.project import ProjectForm

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')


def _populate_big_idea_choices(form):
    """Fill the big_idea_id select with current options."""
    ideas = BigIdea.query.order_by(BigIdea.title).all()
    form.big_idea_id.choices = [(i.id, i.title) for i in ideas]
    return ideas


@projects_bp.route('/')
@login_required
def index():
    projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('projects/index.html', projects=projects)


@projects_bp.route('/<int:project_id>')
@login_required
def detail(project_id):
    project = db.get_or_404(Project, project_id)
    return render_template('projects/detail.html', project=project)


@projects_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new():
    form = ProjectForm()
    ideas = _populate_big_idea_choices(form)

    if not ideas:
        flash('Create a Big Idea first before adding a project.', 'warning')
        return redirect(url_for('big_ideas.new'))

    # Pre-fill from Mind Dump promotion or big_idea_id query param
    from_dump_id = request.args.get('from_dump', type=int)
    preselect_idea = request.args.get('big_idea_id', type=int)
    if request.method == 'GET':
        prefill = request.args.get('prefill', '')
        prefill_category = request.args.get('prefill_category', '')
        if prefill:
            form.title.data = prefill[:200]
        if preselect_idea:
            form.big_idea_id.data = preselect_idea
        if prefill_category in ('work', 'personal'):
            form.category.data = prefill_category

    if form.validate_on_submit():
        link = (form.external_link.data or '').strip()
        cat = form.category.data if form.category.data in ('work', 'personal') else 'work'
        project = Project(
            big_idea_id=form.big_idea_id.data,
            title=form.title.data.strip(),
            description=(form.description.data or '').strip(),
            due_date=form.due_date.data or None,
            external_link=link or None,
            category=cat,
        )
        db.session.add(project)
        db.session.flush()

        if from_dump_id:
            entry = db.session.get(MindDump, from_dump_id)
            if entry:
                entry.status = 'Assigned'
                entry.linked_project_id = project.id

        db.session.commit()
        flash(f'Project "{project.title}" created!', 'success')
        return redirect(url_for('projects.detail', project_id=project.id))

    return render_template('projects/form.html', form=form, project=None)


@projects_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(project_id):
    project = db.get_or_404(Project, project_id)
    form = ProjectForm(obj=project)
    _populate_big_idea_choices(form)

    if form.validate_on_submit():
        link = (form.external_link.data or '').strip()
        project.big_idea_id = form.big_idea_id.data
        project.title = form.title.data.strip()
        project.description = (form.description.data or '').strip()
        project.due_date = form.due_date.data or None
        project.external_link = link or None
        if form.category.data in ('work', 'personal'):
            project.category = form.category.data
        db.session.commit()
        flash(f'Project "{project.title}" updated.', 'success')
        return redirect(url_for('projects.detail', project_id=project.id))

    return render_template('projects/form.html', form=form, project=project)


@projects_bp.route('/<int:project_id>/delete', methods=['POST'])
@login_required
def delete(project_id):
    project = db.get_or_404(Project, project_id)
    title = project.title
    idea_id = project.big_idea_id
    db.session.delete(project)
    db.session.commit()
    flash(f'Project "{title}" and all its tasks deleted.', 'success')
    return redirect(url_for('big_ideas.index'))
