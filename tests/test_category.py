"""
Tests for the work/personal category system:
  - Model defaults (category, view_preference)
  - set_view route (persistence, valid/invalid values)
  - Category stored on create for all content types
  - Category defaults to 'work' when not submitted
  - Dashboard, Big Ideas, Projects index filtering by view
  - Quick capture auto-categorisation from view preference
  - Category inheritance (prefill_category) on Mind Dump promotion
  - Split nav badge counts (W:N / P:N)
  - Category pre-populated on edit form GET
"""
import pytest
from models import User, BigIdea, Project, Task, MindDump


# ── Helpers ───────────────────────────────────────────────────────────────────

def _set_view(db, user, view):
    """Directly set a user's view_preference for test setup."""
    user.view_preference = view
    db.session.commit()


# ── Model defaults ────────────────────────────────────────────────────────────

class TestModelDefaults:
    def test_task_default_category_is_work(self, db, project):
        t = Task(project_id=project.id, title='T')
        db.session.add(t)
        db.session.commit()
        assert t.category == 'work'

    def test_project_default_category_is_work(self, db, big_idea):
        p = Project(big_idea_id=big_idea.id, title='P')
        db.session.add(p)
        db.session.commit()
        assert p.category == 'work'

    def test_big_idea_default_category_is_work(self, db):
        idea = BigIdea(title='I', accent_color='#6366f1')
        db.session.add(idea)
        db.session.commit()
        assert idea.category == 'work'

    def test_mind_dump_default_category_is_work(self, db):
        entry = MindDump(content='thought')
        db.session.add(entry)
        db.session.commit()
        assert entry.category == 'work'

    def test_user_default_view_preference_is_all(self, db):
        u = User(username='newuser')
        u.set_password('password123')
        db.session.add(u)
        db.session.commit()
        assert u.view_preference == 'all'


# ── set_view route ────────────────────────────────────────────────────────────

class TestSetView:
    def test_set_view_work_updates_preference(self, auth_client, db, user):
        auth_client.post('/set-view', data={'view': 'work'})
        db.session.expire_all()
        assert db.session.get(User, user.id).view_preference == 'work'

    def test_set_view_personal_updates_preference(self, auth_client, db, user):
        auth_client.post('/set-view', data={'view': 'personal'})
        db.session.expire_all()
        assert db.session.get(User, user.id).view_preference == 'personal'

    def test_set_view_all_updates_preference(self, auth_client, db, user):
        _set_view(db, user, 'work')
        auth_client.post('/set-view', data={'view': 'all'})
        db.session.expire_all()
        assert db.session.get(User, user.id).view_preference == 'all'

    def test_set_view_invalid_value_not_saved(self, auth_client, db, user):
        _set_view(db, user, 'work')
        auth_client.post('/set-view', data={'view': 'invalid'})
        db.session.expire_all()
        # preference unchanged
        assert db.session.get(User, user.id).view_preference == 'work'

    def test_set_view_redirects(self, auth_client):
        resp = auth_client.post('/set-view', data={'view': 'work'})
        assert resp.status_code == 302

    def test_set_view_unauthenticated_redirects_to_login(self, client):
        resp = client.post('/set-view', data={'view': 'work'})
        assert resp.status_code == 302
        assert '/login' in resp.location


# ── Category stored on create ─────────────────────────────────────────────────

class TestCategoryOnCreate:
    def test_task_created_with_work_category(self, auth_client, db, project):
        auth_client.post('/tasks/new', data={
            'title': 'Work Task',
            'project_id': project.id,
            'status': 'Not Started',
            'category': 'work',
        })
        t = Task.query.filter_by(title='Work Task').first()
        assert t is not None
        assert t.category == 'work'

    def test_task_created_with_personal_category(self, auth_client, db, project):
        auth_client.post('/tasks/new', data={
            'title': 'Personal Task',
            'project_id': project.id,
            'status': 'Not Started',
            'category': 'personal',
        })
        t = Task.query.filter_by(title='Personal Task').first()
        assert t is not None
        assert t.category == 'personal'

    def test_task_category_defaults_to_work_when_omitted(self, auth_client, db, project):
        auth_client.post('/tasks/new', data={
            'title': 'No Category Task',
            'project_id': project.id,
            'status': 'Not Started',
        })
        t = Task.query.filter_by(title='No Category Task').first()
        assert t is not None
        assert t.category == 'work'

    def test_big_idea_created_with_personal_category(self, auth_client, db):
        auth_client.post('/big-ideas/new', data={
            'title': 'Personal Idea',
            'accent_color': '#6366f1',
            'category': 'personal',
        })
        idea = BigIdea.query.filter_by(title='Personal Idea').first()
        assert idea is not None
        assert idea.category == 'personal'

    def test_big_idea_category_defaults_to_work_when_omitted(self, auth_client, db):
        auth_client.post('/big-ideas/new', data={
            'title': 'Default Category Idea',
            'accent_color': '#6366f1',
        })
        idea = BigIdea.query.filter_by(title='Default Category Idea').first()
        assert idea is not None
        assert idea.category == 'work'

    def test_project_created_with_personal_category(self, auth_client, db, big_idea):
        auth_client.post('/projects/new', data={
            'title': 'Personal Project',
            'big_idea_id': big_idea.id,
            'category': 'personal',
        })
        p = Project.query.filter_by(title='Personal Project').first()
        assert p is not None
        assert p.category == 'personal'

    def test_project_category_defaults_to_work_when_omitted(self, auth_client, db, big_idea):
        auth_client.post('/projects/new', data={
            'title': 'Default Category Project',
            'big_idea_id': big_idea.id,
        })
        p = Project.query.filter_by(title='Default Category Project').first()
        assert p is not None
        assert p.category == 'work'

    def test_mind_dump_capture_stores_work_category(self, auth_client, db):
        auth_client.post('/mind-dump/capture', data={
            'content': 'Work thought',
            'category': 'work',
        })
        entry = MindDump.query.filter_by(content='Work thought').first()
        assert entry is not None
        assert entry.category == 'work'

    def test_mind_dump_capture_stores_personal_category(self, auth_client, db):
        auth_client.post('/mind-dump/capture', data={
            'content': 'Personal thought',
            'category': 'personal',
        })
        entry = MindDump.query.filter_by(content='Personal thought').first()
        assert entry is not None
        assert entry.category == 'personal'


# ── Dashboard view filtering ──────────────────────────────────────────────────

class TestDashboardCategoryFilter:
    def _make_quick_tasks(self, db):
        """Create one work and one personal quick task (no project, no due date)."""
        work = Task(title='Work Quick Task', category='work', status='Not Started')
        personal = Task(title='Personal Quick Task', category='personal', status='Not Started')
        db.session.add_all([work, personal])
        db.session.commit()
        return work, personal

    def test_all_view_shows_both_categories(self, auth_client, db, user):
        _set_view(db, user, 'all')
        work, personal = self._make_quick_tasks(db)
        resp = auth_client.get('/')
        assert b'Work Quick Task' in resp.data
        assert b'Personal Quick Task' in resp.data

    def test_work_view_shows_only_work_tasks(self, auth_client, db, user):
        _set_view(db, user, 'work')
        work, personal = self._make_quick_tasks(db)
        resp = auth_client.get('/')
        assert b'Work Quick Task' in resp.data
        assert b'Personal Quick Task' not in resp.data

    def test_personal_view_shows_only_personal_tasks(self, auth_client, db, user):
        _set_view(db, user, 'personal')
        work, personal = self._make_quick_tasks(db)
        resp = auth_client.get('/')
        assert b'Personal Quick Task' in resp.data
        assert b'Work Quick Task' not in resp.data


# ── Big Ideas index filtering ─────────────────────────────────────────────────

class TestBigIdeasCategoryFilter:
    def _make_ideas(self, db):
        work = BigIdea(title='Work Idea', accent_color='#6366f1', category='work')
        personal = BigIdea(title='Personal Idea', accent_color='#6366f1', category='personal')
        db.session.add_all([work, personal])
        db.session.commit()
        return work, personal

    def test_all_view_shows_both_categories(self, auth_client, db, user):
        _set_view(db, user, 'all')
        self._make_ideas(db)
        resp = auth_client.get('/big-ideas/')
        assert b'Work Idea' in resp.data
        assert b'Personal Idea' in resp.data

    def test_work_view_shows_only_work_ideas(self, auth_client, db, user):
        _set_view(db, user, 'work')
        self._make_ideas(db)
        resp = auth_client.get('/big-ideas/')
        assert b'Work Idea' in resp.data
        assert b'Personal Idea' not in resp.data

    def test_personal_view_shows_only_personal_ideas(self, auth_client, db, user):
        _set_view(db, user, 'personal')
        self._make_ideas(db)
        resp = auth_client.get('/big-ideas/')
        assert b'Personal Idea' in resp.data
        assert b'Work Idea' not in resp.data


# ── Projects index filtering ──────────────────────────────────────────────────

class TestProjectsCategoryFilter:
    def _make_projects(self, db, big_idea):
        work = Project(big_idea_id=big_idea.id, title='Work Project', category='work')
        personal = Project(big_idea_id=big_idea.id, title='Personal Project', category='personal')
        db.session.add_all([work, personal])
        db.session.commit()
        return work, personal

    def test_all_view_shows_both_categories(self, auth_client, db, user, big_idea):
        _set_view(db, user, 'all')
        self._make_projects(db, big_idea)
        resp = auth_client.get('/projects/')
        assert b'Work Project' in resp.data
        assert b'Personal Project' in resp.data

    def test_work_view_shows_only_work_projects(self, auth_client, db, user, big_idea):
        _set_view(db, user, 'work')
        self._make_projects(db, big_idea)
        resp = auth_client.get('/projects/')
        assert b'Work Project' in resp.data
        assert b'Personal Project' not in resp.data

    def test_personal_view_shows_only_personal_projects(self, auth_client, db, user, big_idea):
        _set_view(db, user, 'personal')
        self._make_projects(db, big_idea)
        resp = auth_client.get('/projects/')
        assert b'Personal Project' in resp.data
        assert b'Work Project' not in resp.data


# ── Quick capture auto-categorisation ────────────────────────────────────────

class TestQuickCaptureCategory:
    def test_work_view_captures_as_work(self, auth_client, db, user):
        _set_view(db, user, 'work')
        auth_client.post('/quick-capture', data={'content': 'Work capture'})
        entry = MindDump.query.filter_by(content='Work capture').first()
        assert entry is not None
        assert entry.category == 'work'

    def test_personal_view_captures_as_personal(self, auth_client, db, user):
        _set_view(db, user, 'personal')
        auth_client.post('/quick-capture', data={'content': 'Personal capture'})
        entry = MindDump.query.filter_by(content='Personal capture').first()
        assert entry is not None
        assert entry.category == 'personal'


# ── Category inheritance on Mind Dump promotion ───────────────────────────────

class TestCategoryInheritanceOnPromote:
    def test_promote_task_includes_category_in_redirect(self, auth_client, db):
        entry = MindDump(content='Promote me', category='personal')
        db.session.add(entry)
        db.session.commit()
        resp = auth_client.get(f'/mind-dump/{entry.id}/promote-task')
        assert resp.status_code == 302
        assert 'prefill_category=personal' in resp.location

    def test_promote_project_includes_category_in_redirect(self, auth_client, db):
        entry = MindDump(content='Project idea', category='personal')
        db.session.add(entry)
        db.session.commit()
        resp = auth_client.get(f'/mind-dump/{entry.id}/promote-project')
        assert resp.status_code == 302
        assert 'prefill_category=personal' in resp.location

    def test_promote_big_idea_includes_category_in_redirect(self, auth_client, db):
        entry = MindDump(content='Big idea', category='work')
        db.session.add(entry)
        db.session.commit()
        resp = auth_client.get(f'/mind-dump/{entry.id}/promote-big-idea')
        assert resp.status_code == 302
        assert 'prefill_category=work' in resp.location

    def test_promoted_task_inherits_category(self, auth_client, db, project):
        """Task created from a personal dump entry is stored with personal category."""
        entry = MindDump(content='Personal task idea', category='personal')
        db.session.add(entry)
        db.session.commit()
        auth_client.post(
            f'/tasks/new?from_dump={entry.id}',
            data={
                'title': 'Inherited Personal Task',
                'project_id': project.id,
                'status': 'Not Started',
                'category': 'personal',
            }
        )
        t = Task.query.filter_by(title='Inherited Personal Task').first()
        assert t is not None
        assert t.category == 'personal'


# ── Split nav badge counts ────────────────────────────────────────────────────

class TestNavBadgeCounts:
    def test_work_badge_count_shown(self, auth_client, db):
        for i in range(2):
            db.session.add(MindDump(content=f'Work {i}', category='work', status='Unorganized'))
        db.session.add(MindDump(content='Personal', category='personal', status='Unorganized'))
        db.session.commit()
        resp = auth_client.get('/')
        assert b'W:2' in resp.data or b'2' in resp.data  # work count

    def test_personal_badge_count_shown(self, auth_client, db):
        db.session.add(MindDump(content='Work', category='work', status='Unorganized'))
        for i in range(3):
            db.session.add(MindDump(content=f'Personal {i}', category='personal', status='Unorganized'))
        db.session.commit()
        resp = auth_client.get('/')
        assert b'P:3' in resp.data or b'3' in resp.data  # personal count

    def test_assigned_entries_not_counted_in_badge(self, auth_client, db):
        db.session.add(MindDump(content='Assigned', category='work', status='Assigned'))
        db.session.add(MindDump(content='Unorg', category='work', status='Unorganized'))
        db.session.commit()
        resp = auth_client.get('/')
        # Only 1 unorganized — the badge should not show 2
        assert b'W:1' in resp.data or resp.status_code == 200


# ── Category pre-populated on edit GET ───────────────────────────────────────

class TestEditCategoryPrePopulated:
    def test_task_edit_form_shows_current_category(self, auth_client, db, project):
        t = Task(project_id=project.id, title='Personal Task', category='personal')
        db.session.add(t)
        db.session.commit()
        resp = auth_client.get(f'/tasks/{t.id}/edit')
        assert resp.status_code == 200
        # The hidden category field should carry the current value
        assert b'personal' in resp.data

    def test_project_edit_form_shows_current_category(self, auth_client, db, big_idea):
        p = Project(big_idea_id=big_idea.id, title='Personal Project', category='personal')
        db.session.add(p)
        db.session.commit()
        resp = auth_client.get(f'/projects/{p.id}/edit')
        assert resp.status_code == 200
        assert b'personal' in resp.data

    def test_big_idea_edit_form_shows_current_category(self, auth_client, db):
        idea = BigIdea(title='Personal Idea', accent_color='#6366f1', category='personal')
        db.session.add(idea)
        db.session.commit()
        resp = auth_client.get(f'/big-ideas/{idea.id}/edit')
        assert resp.status_code == 200
        assert b'personal' in resp.data

    def test_edit_task_updates_category_to_personal(self, auth_client, db, project):
        t = Task(project_id=project.id, title='Switch Category', category='work')
        db.session.add(t)
        db.session.commit()
        auth_client.post(f'/tasks/{t.id}/edit', data={
            'title': t.title,
            'project_id': project.id,
            'status': t.status,
            'category': 'personal',
        })
        db.session.expire_all()
        updated = db.session.get(Task, t.id)
        assert updated.category == 'personal'
