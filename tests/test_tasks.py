"""
Tests for Tasks CRUD, pin/unpin One Thing, complete, and external link.
"""
import pytest
from datetime import date, datetime, timezone
from models import Task, Project


class TestCreateTask:
    def test_create_redirects_to_project_detail(self, auth_client, db, project):
        resp = auth_client.post('/tasks/new', data={
            'title': 'New Task',
            'project_id': project.id,
            'status': 'Not Started',
        })
        assert resp.status_code == 302
        assert f'/projects/{project.id}' in resp.location

    def test_create_stores_title(self, auth_client, db, project):
        auth_client.post('/tasks/new', data={
            'title': 'My Stored Task',
            'project_id': project.id,
            'status': 'Not Started',
        })
        assert Task.query.filter_by(title='My Stored Task').first() is not None

    def test_create_without_due_date_is_valid(self, auth_client, db, project):
        resp = auth_client.post('/tasks/new', data={
            'title': 'No Due Date',
            'project_id': project.id,
            'status': 'Not Started',
        })
        assert resp.status_code == 302
        t = Task.query.filter_by(title='No Due Date').first()
        assert t.due_date is None

    def test_create_without_status_uses_default(self, auth_client, db, project):
        auth_client.post('/tasks/new', data={
            'title': 'Default Status',
            'project_id': project.id,
        })
        t = Task.query.filter_by(title='Default Status').first()
        assert t.status == 'Not Started'

    def test_create_stores_due_date(self, auth_client, db, project):
        auth_client.post('/tasks/new', data={
            'title': 'Dated Task',
            'project_id': project.id,
            'status': 'Not Started',
            'due_date': '2030-12-31',
        })
        t = Task.query.filter_by(title='Dated Task').first()
        assert t.due_date == date(2030, 12, 31)

    def test_create_empty_title_fails(self, auth_client, db, project):
        before = Task.query.count()
        resp = auth_client.post('/tasks/new', data={
            'title': '',
            'project_id': project.id,
        })
        assert resp.status_code == 200
        assert Task.query.count() == before

    def test_create_accessible_when_no_projects(self, auth_client, db):
        resp = auth_client.get('/tasks/new')
        assert resp.status_code == 200

    def test_create_from_mind_dump_marks_assigned(self, auth_client, db, project, mind_dump_entry):
        resp = auth_client.post(
            f'/tasks/new?from_dump={mind_dump_entry.id}',
            data={
                'title': 'From Dump',
                'project_id': project.id,
                'status': 'Not Started',
            }
        )
        assert resp.status_code == 302
        from models import MindDump
        db.session.expire_all()
        updated = db.session.get(MindDump, mind_dump_entry.id)
        assert updated.status == 'Assigned'


class TestEditTask:
    def test_edit_form_accessible(self, auth_client, task):
        resp = auth_client.get(f'/tasks/{task.id}/edit')
        assert resp.status_code == 200

    def test_edit_form_prepopulated(self, auth_client, task):
        resp = auth_client.get(f'/tasks/{task.id}/edit')
        assert task.title.encode() in resp.data

    def test_edit_updates_title(self, auth_client, db, task, project):
        resp = auth_client.post(f'/tasks/{task.id}/edit', data={
            'title': 'Renamed Task',
            'project_id': project.id,
            'status': 'Not Started',
        })
        assert resp.status_code == 302
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.title == 'Renamed Task'

    def test_edit_updates_status(self, auth_client, db, task, project):
        auth_client.post(f'/tasks/{task.id}/edit', data={
            'title': task.title,
            'project_id': project.id,
            'status': 'In Progress',
        })
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.status == 'In Progress'

    def test_edit_to_done_sets_completed_at(self, auth_client, db, task, project):
        auth_client.post(f'/tasks/{task.id}/edit', data={
            'title': task.title,
            'project_id': project.id,
            'status': 'Done',
        })
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.completed_at is not None

    def test_edit_from_done_clears_completed_at(self, auth_client, db, task, project):
        task.status = 'Done'
        task.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        auth_client.post(f'/tasks/{task.id}/edit', data={
            'title': task.title,
            'project_id': project.id,
            'status': 'Not Started',
        })
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.completed_at is None

    def test_edit_nonexistent_returns_404(self, auth_client):
        resp = auth_client.get('/tasks/99999/edit')
        assert resp.status_code == 404


class TestDeleteTask:
    def test_delete_removes_task(self, auth_client, db, task):
        task_id = task.id
        before = Task.query.count()
        auth_client.post(f'/tasks/{task_id}/delete')
        assert Task.query.count() == before - 1
        assert db.session.get(Task, task_id) is None

    def test_delete_redirects_to_project(self, auth_client, db, task):
        resp = auth_client.post(f'/tasks/{task.id}/delete')
        assert resp.status_code == 302
        assert f'/projects/{task.project_id}' in resp.location

    def test_delete_nonexistent_returns_404(self, auth_client):
        resp = auth_client.post('/tasks/99999/delete')
        assert resp.status_code == 404


class TestPinOneThingTask:
    def test_pin_sets_is_pinned(self, auth_client, db, task):
        resp = auth_client.post(f'/tasks/{task.id}/pin')
        assert resp.status_code == 302
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.is_pinned is True

    def test_pin_new_task_unpins_previous(self, auth_client, db, project):
        t1 = Task(project_id=project.id, title='T1', is_pinned=True)
        t2 = Task(project_id=project.id, title='T2')
        db.session.add_all([t1, t2])
        db.session.commit()

        auth_client.post(f'/tasks/{t2.id}/pin')
        db.session.expire_all()

        assert db.session.get(Task, t1.id).is_pinned is False
        assert db.session.get(Task, t2.id).is_pinned is True

    def test_only_one_task_pinned_at_a_time(self, auth_client, db, project):
        tasks = [Task(project_id=project.id, title=f'T{i}') for i in range(5)]
        db.session.add_all(tasks)
        db.session.commit()

        # Pin each in sequence
        for t in tasks:
            auth_client.post(f'/tasks/{t.id}/pin')

        db.session.expire_all()
        pinned = Task.query.filter_by(is_pinned=True).all()
        assert len(pinned) == 1
        assert pinned[0].id == tasks[-1].id

    def test_unpin_clears_is_pinned(self, auth_client, db, task):
        task.is_pinned = True
        db.session.commit()
        resp = auth_client.post(f'/tasks/{task.id}/unpin')
        assert resp.status_code == 302
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.is_pinned is False

    def test_pin_nonexistent_returns_404(self, auth_client):
        resp = auth_client.post('/tasks/99999/pin')
        assert resp.status_code == 404


class TestCompleteTask:
    def test_complete_sets_status_done(self, auth_client, db, task):
        resp = auth_client.post(f'/tasks/{task.id}/complete')
        assert resp.status_code == 302
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.status == 'Done'

    def test_complete_sets_completed_at(self, auth_client, db, task):
        auth_client.post(f'/tasks/{task.id}/complete')
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.completed_at is not None

    def test_complete_clears_pin(self, auth_client, db, task):
        task.is_pinned = True
        db.session.commit()
        auth_client.post(f'/tasks/{task.id}/complete')
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.is_pinned is False

    def test_complete_nonexistent_returns_404(self, auth_client):
        resp = auth_client.post('/tasks/99999/complete')
        assert resp.status_code == 404


class TestExternalLink:
    def test_task_with_external_link_stored(self, auth_client, db, project):
        auth_client.post('/tasks/new', data={
            'title': 'External Task',
            'project_id': project.id,
            'status': 'Not Started',
            'external_link': 'https://notion.so/abc',
        })
        t = Task.query.filter_by(title='External Task').first()
        assert t.external_link == 'https://notion.so/abc'

    def test_task_external_link_badge_shown_in_project_detail(self, auth_client, db, task):
        task.external_link = 'https://trello.com/c/xyz'
        db.session.commit()
        resp = auth_client.get(f'/projects/{task.project_id}')
        assert b'Tracked externally' in resp.data
