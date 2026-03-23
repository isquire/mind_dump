"""Big Ideas: CRUD for top-level goal/theme containers."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from models import db, BigIdea, MindDump
from forms.big_idea import BigIdeaForm

big_ideas_bp = Blueprint('big_ideas', __name__, url_prefix='/big-ideas')


@big_ideas_bp.route('/')
@login_required
def index():
    view = current_user.view_preference or 'all'
    q = BigIdea.query.order_by(BigIdea.created_at.desc())
    if view in ('work', 'personal'):
        q = q.filter(BigIdea.category == view)
    ideas = q.all()
    return render_template('big_ideas/index.html', ideas=ideas)


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
        return redirect(url_for('big_ideas.index'))

    return render_template('big_ideas/form.html', form=form, idea=None)


@big_ideas_bp.route('/<int:idea_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(idea_id):
    idea = db.get_or_404(BigIdea, idea_id)
    form = BigIdeaForm(obj=idea)

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
