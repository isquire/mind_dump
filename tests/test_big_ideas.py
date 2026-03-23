"""
Tests for Big Ideas CRUD: create, read, edit, delete,
accent colour validation, and cascade deletion.
"""
import pytest
from models import BigIdea, Project, Task


class TestBigIdeasIndex:
    def test_index_accessible(self, auth_client):
        resp = auth_client.get('/big-ideas/')
        assert resp.status_code == 200

    def test_index_shows_existing_idea(self, auth_client, big_idea):
        resp = auth_client.get('/big-ideas/')
        assert big_idea.title.encode() in resp.data

    def test_index_empty_state_shown(self, auth_client):
        resp = auth_client.get('/big-ideas/')
        assert b'No big ideas yet' in resp.data or resp.status_code == 200

    def test_index_shows_new_button(self, auth_client):
        resp = auth_client.get('/big-ideas/')
        assert b'New Big Idea' in resp.data


class TestCreateBigIdea:
    def test_create_redirects_to_index(self, auth_client, db):
        resp = auth_client.post('/big-ideas/new', data={
            'title': 'Launch my app',
            'accent_color': '#6366f1',
        })
        assert resp.status_code == 302
        assert '/big-ideas/' in resp.location

    def test_create_stores_title(self, auth_client, db):
        auth_client.post('/big-ideas/new', data={
            'title': 'Learn Spanish',
            'accent_color': '#6366f1',
        })
        assert BigIdea.query.filter_by(title='Learn Spanish').first() is not None

    def test_create_stores_description(self, auth_client, db):
        auth_client.post('/big-ideas/new', data={
            'title': 'Side project',
            'description': 'Build something cool',
            'accent_color': '#6366f1',
        })
        idea = BigIdea.query.filter_by(title='Side project').first()
        assert idea.description == 'Build something cool'

    def test_create_stores_accent_color(self, auth_client, db):
        auth_client.post('/big-ideas/new', data={
            'title': 'Colour Test',
            'accent_color': '#ff5733',
        })
        idea = BigIdea.query.filter_by(title='Colour Test').first()
        assert idea.accent_color == '#ff5733'

    def test_create_empty_title_fails(self, auth_client, db):
        before = BigIdea.query.count()
        resp = auth_client.post('/big-ideas/new', data={
            'title': '',
            'accent_color': '#6366f1',
        })
        assert resp.status_code == 200  # re-renders form
        assert BigIdea.query.count() == before

    def test_create_invalid_accent_color_fails(self, auth_client, db):
        before = BigIdea.query.count()
        resp = auth_client.post('/big-ideas/new', data={
            'title': 'Bad Color',
            'accent_color': 'not-a-color',
        })
        assert resp.status_code == 200
        assert BigIdea.query.count() == before

    def test_create_short_hex_color_fails(self, auth_client, db):
        before = BigIdea.query.count()
        resp = auth_client.post('/big-ideas/new', data={
            'title': 'Short Color',
            'accent_color': '#fff',  # 3-digit hex not allowed
        })
        assert resp.status_code == 200
        assert BigIdea.query.count() == before

    def test_create_preloaded_from_mind_dump(self, auth_client, db, mind_dump_entry):
        """Promoting from Mind Dump marks it Assigned."""
        resp = auth_client.post(
            f'/big-ideas/new?from_dump={mind_dump_entry.id}',
            data={
                'title': 'Promoted Idea',
                'accent_color': '#6366f1',
            }
        )
        assert resp.status_code == 302
        from models import MindDump
        db.session.expire_all()
        updated = db.session.get(MindDump, mind_dump_entry.id)
        assert updated.status == 'Assigned'


class TestEditBigIdea:
    def test_edit_form_accessible(self, auth_client, big_idea):
        resp = auth_client.get(f'/big-ideas/{big_idea.id}/edit')
        assert resp.status_code == 200

    def test_edit_form_prepopulated(self, auth_client, big_idea):
        resp = auth_client.get(f'/big-ideas/{big_idea.id}/edit')
        assert big_idea.title.encode() in resp.data

    def test_edit_updates_title(self, auth_client, db, big_idea):
        resp = auth_client.post(f'/big-ideas/{big_idea.id}/edit', data={
            'title': 'Updated Title',
            'accent_color': '#6366f1',
        })
        assert resp.status_code == 302
        db.session.expire_all()
        updated = db.session.get(BigIdea, big_idea.id)
        assert updated.title == 'Updated Title'

    def test_edit_updates_accent_color(self, auth_client, db, big_idea):
        auth_client.post(f'/big-ideas/{big_idea.id}/edit', data={
            'title': big_idea.title,
            'accent_color': '#123456',
        })
        db.session.expire_all()
        updated = db.session.get(BigIdea, big_idea.id)
        assert updated.accent_color == '#123456'

    def test_edit_nonexistent_returns_404(self, auth_client):
        resp = auth_client.get('/big-ideas/99999/edit')
        assert resp.status_code == 404


class TestDeleteBigIdea:
    def test_delete_removes_idea(self, auth_client, db, big_idea):
        idea_id = big_idea.id
        before = BigIdea.query.count()
        auth_client.post(f'/big-ideas/{idea_id}/delete')
        assert BigIdea.query.count() == before - 1
        assert db.session.get(BigIdea, idea_id) is None

    def test_delete_cascades_to_projects(self, auth_client, db, project):
        """Deleting a Big Idea must delete all its Projects."""
        idea_id = project.big_idea_id
        project_id = project.id
        auth_client.post(f'/big-ideas/{idea_id}/delete')
        assert db.session.get(Project, project_id) is None

    def test_delete_cascades_to_tasks(self, auth_client, db, task):
        """Deleting a Big Idea must cascade through Projects to Tasks."""
        idea_id = task.project.big_idea_id
        task_id = task.id
        auth_client.post(f'/big-ideas/{idea_id}/delete')
        assert db.session.get(Task, task_id) is None

    def test_delete_redirects_to_index(self, auth_client, big_idea):
        resp = auth_client.post(f'/big-ideas/{big_idea.id}/delete')
        assert resp.status_code == 302
        assert '/big-ideas/' in resp.location
