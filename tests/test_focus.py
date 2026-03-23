"""
Tests for Focus Mode: view rendering, complete, snooze,
and verification that navigation is absent.
"""
import pytest
from datetime import date, timedelta
from models import Task


class TestFocusView:
    def test_focus_view_accessible(self, auth_client, task):
        resp = auth_client.get(f'/focus/{task.id}')
        assert resp.status_code == 200

    def test_focus_view_shows_task_title(self, auth_client, task):
        resp = auth_client.get(f'/focus/{task.id}')
        assert task.title.encode() in resp.data

    def test_focus_view_shows_notes(self, auth_client, db, task):
        task.notes = '<p>Important context for this task.</p>'
        db.session.commit()
        resp = auth_client.get(f'/focus/{task.id}')
        assert b'Important context for this task.' in resp.data

    def test_focus_view_shows_due_date(self, auth_client, db, task):
        task.due_date = date(2030, 8, 15)
        db.session.commit()
        resp = auth_client.get(f'/focus/{task.id}')
        assert b'2030' in resp.data or b'15 Aug' in resp.data

    def test_focus_view_shows_open_in_planner_button(self, auth_client, db, task):
        task.external_link = 'https://linear.app/board'
        db.session.commit()
        resp = auth_client.get(f'/focus/{task.id}')
        assert b'Open in Planner' in resp.data

    def test_focus_view_no_open_in_planner_without_link(self, auth_client, task):
        resp = auth_client.get(f'/focus/{task.id}')
        assert b'Open in Planner' not in resp.data

    def test_focus_view_has_mark_complete_button(self, auth_client, task):
        resp = auth_client.get(f'/focus/{task.id}')
        assert b'Mark Complete' in resp.data

    def test_focus_view_has_snooze_button(self, auth_client, task):
        resp = auth_client.get(f'/focus/{task.id}')
        assert b'Snooze to Tomorrow' in resp.data

    def test_focus_view_has_no_main_navbar(self, auth_client, task):
        """Focus mode must hide the main navigation for distraction-free work."""
        resp = auth_client.get(f'/focus/{task.id}')
        # The focus template uses focus_base.html which has no <nav class="navbar">
        assert b'navbar-expand' not in resp.data

    def test_focus_nonexistent_returns_404(self, auth_client):
        resp = auth_client.get('/focus/99999')
        assert resp.status_code == 404


class TestFocusComplete:
    def test_complete_sets_status_done(self, auth_client, db, task):
        resp = auth_client.post(f'/focus/{task.id}/complete')
        assert resp.status_code == 200  # renders completion screen
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.status == 'Done'

    def test_complete_sets_completed_at(self, auth_client, db, task):
        auth_client.post(f'/focus/{task.id}/complete')
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.completed_at is not None

    def test_complete_clears_pin(self, auth_client, db, task):
        task.is_pinned = True
        db.session.commit()
        auth_client.post(f'/focus/{task.id}/complete')
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.is_pinned is False

    def test_complete_renders_done_state(self, auth_client, task):
        resp = auth_client.post(f'/focus/{task.id}/complete')
        assert b'Done' in resp.data
        assert b'Great work' in resp.data

    def test_complete_shows_back_to_dashboard_link(self, auth_client, task):
        resp = auth_client.post(f'/focus/{task.id}/complete')
        assert b'Dashboard' in resp.data

    def test_complete_nonexistent_returns_404(self, auth_client):
        resp = auth_client.post('/focus/99999/complete')
        assert resp.status_code == 404


class TestFocusSnooze:
    def test_snooze_moves_due_date_to_tomorrow(self, auth_client, db, task):
        task.due_date = date.today()
        db.session.commit()
        resp = auth_client.post(f'/focus/{task.id}/snooze')
        assert resp.status_code == 302
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.due_date == date.today() + timedelta(days=1)

    def test_snooze_without_due_date_sets_tomorrow(self, auth_client, db, task):
        """Snoozing a task with no due date should set it to tomorrow."""
        assert task.due_date is None
        auth_client.post(f'/focus/{task.id}/snooze')
        db.session.expire_all()
        updated = db.session.get(Task, task.id)
        assert updated.due_date == date.today() + timedelta(days=1)

    def test_snooze_redirects_to_dashboard(self, auth_client, task):
        resp = auth_client.post(f'/focus/{task.id}/snooze')
        assert resp.status_code == 302
        assert '/' in resp.location

    def test_snooze_overdue_task_moves_to_tomorrow(self, auth_client, db, overdue_task):
        resp = auth_client.post(f'/focus/{overdue_task.id}/snooze')
        db.session.expire_all()
        updated = db.session.get(Task, overdue_task.id)
        assert updated.due_date == date.today() + timedelta(days=1)

    def test_snooze_nonexistent_returns_404(self, auth_client):
        resp = auth_client.post('/focus/99999/snooze')
        assert resp.status_code == 404
