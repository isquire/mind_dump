"""
Tests for Projects CRUD: create, read (detail), edit, delete,
external link, progress bar, and cascade deletion of tasks.
"""
import pytest
from datetime import date, timedelta
from models import Project, Task


class TestProjectsList:
    def test_projects_index_accessible(self, auth_client):
        resp = auth_client.get('/projects/')
        assert resp.status_code == 200

    def test_projects_index_shows_project(self, auth_client, project):
        resp = auth_client.get('/projects/')
        assert project.title.encode() in resp.data


class TestProjectDetail:
    def test_detail_accessible(self, auth_client, project):
        resp = auth_client.get(f'/projects/{project.id}')
        assert resp.status_code == 200

    def test_detail_shows_project_title(self, auth_client, project):
        resp = auth_client.get(f'/projects/{project.id}')
        assert project.title.encode() in resp.data

    def test_detail_shows_tasks(self, auth_client, db, project):
        db.session.add(Task(project_id=project.id, title='Visible Task'))
        db.session.commit()
        resp = auth_client.get(f'/projects/{project.id}')
        assert b'Visible Task' in resp.data

    def test_detail_shows_progress_bar(self, auth_client, db, project):
        db.session.add(Task(project_id=project.id, title='T', status='Done'))
        db.session.commit()
        resp = auth_client.get(f'/projects/{project.id}')
        assert b'progress-bar' in resp.data

    def test_detail_shows_external_link_button(self, auth_client, db, project):
        project.external_link = 'https://linear.app/board'
        db.session.commit()
        resp = auth_client.get(f'/projects/{project.id}')
        assert b'Open in Planner' in resp.data
        assert b'Tracked externally' in resp.data

    def test_detail_no_external_link_button_when_not_set(self, auth_client, project):
        resp = auth_client.get(f'/projects/{project.id}')
        assert b'Open in Planner' not in resp.data

    def test_detail_nonexistent_returns_404(self, auth_client):
        resp = auth_client.get('/projects/99999')
        assert resp.status_code == 404


class TestCreateProject:
    def test_create_redirects_to_detail(self, auth_client, db, big_idea):
        resp = auth_client.post('/projects/new', data={
            'title': 'New Project',
            'big_idea_id': big_idea.id,
        })
        assert resp.status_code == 302
        assert '/projects/' in resp.location

    def test_create_stores_title(self, auth_client, db, big_idea):
        auth_client.post('/projects/new', data={
            'title': 'Stored Project',
            'big_idea_id': big_idea.id,
        })
        assert Project.query.filter_by(title='Stored Project').first() is not None

    def test_create_stores_due_date(self, auth_client, db, big_idea):
        auth_client.post('/projects/new', data={
            'title': 'Dated Project',
            'big_idea_id': big_idea.id,
            'due_date': '2030-06-15',
        })
        p = Project.query.filter_by(title='Dated Project').first()
        assert p.due_date == date(2030, 6, 15)

    def test_create_without_due_date_is_valid(self, auth_client, db, big_idea):
        resp = auth_client.post('/projects/new', data={
            'title': 'No Date Project',
            'big_idea_id': big_idea.id,
        })
        assert resp.status_code == 302
        p = Project.query.filter_by(title='No Date Project').first()
        assert p.due_date is None

    def test_create_empty_title_fails(self, auth_client, db, big_idea):
        before = Project.query.count()
        resp = auth_client.post('/projects/new', data={
            'title': '',
            'big_idea_id': big_idea.id,
        })
        assert resp.status_code == 200
        assert Project.query.count() == before

    def test_create_redirects_to_big_ideas_when_no_ideas_exist(self, auth_client, db):
        resp = auth_client.get('/projects/new')
        assert resp.status_code == 302
        assert '/big-ideas/new' in resp.location

    def test_create_from_mind_dump_marks_assigned(self, auth_client, db, big_idea, mind_dump_entry):
        resp = auth_client.post(
            f'/projects/new?from_dump={mind_dump_entry.id}',
            data={
                'title': 'Promoted Project',
                'big_idea_id': big_idea.id,
            }
        )
        assert resp.status_code == 302
        from models import MindDump
        db.session.expire_all()
        updated = db.session.get(MindDump, mind_dump_entry.id)
        assert updated.status == 'Assigned'


class TestEditProject:
    def test_edit_form_accessible(self, auth_client, project):
        resp = auth_client.get(f'/projects/{project.id}/edit')
        assert resp.status_code == 200

    def test_edit_updates_title(self, auth_client, db, project, big_idea):
        resp = auth_client.post(f'/projects/{project.id}/edit', data={
            'title': 'Renamed Project',
            'big_idea_id': big_idea.id,
        })
        assert resp.status_code == 302
        db.session.expire_all()
        updated = db.session.get(Project, project.id)
        assert updated.title == 'Renamed Project'

    def test_edit_clears_external_link_when_blank(self, auth_client, db, project, big_idea):
        project.external_link = 'https://example.com'
        db.session.commit()
        auth_client.post(f'/projects/{project.id}/edit', data={
            'title': project.title,
            'big_idea_id': big_idea.id,
            'external_link': '',
        })
        db.session.expire_all()
        updated = db.session.get(Project, project.id)
        assert updated.external_link is None


class TestDeleteProject:
    def test_delete_removes_project(self, auth_client, db, project):
        project_id = project.id
        before = Project.query.count()
        auth_client.post(f'/projects/{project_id}/delete')
        assert Project.query.count() == before - 1
        assert db.session.get(Project, project_id) is None

    def test_delete_cascades_to_tasks(self, auth_client, db, task):
        project_id = task.project_id
        task_id = task.id
        auth_client.post(f'/projects/{project_id}/delete')
        assert db.session.get(Task, task_id) is None

    def test_delete_redirects_to_big_ideas(self, auth_client, project):
        resp = auth_client.post(f'/projects/{project.id}/delete')
        assert resp.status_code == 302
