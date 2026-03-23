"""
Tests for authentication: login, logout, session management,
inactivity timeout, open-redirect protection, and route guarding.
"""
import time
import pytest
from models import User


class TestLoginPage:
    def test_login_page_accessible(self, client):
        resp = client.get('/login')
        assert resp.status_code == 200

    def test_login_page_contains_form_fields(self, client):
        resp = client.get('/login')
        assert b'username' in resp.data
        assert b'password' in resp.data

    def test_authenticated_user_redirected_from_login(self, auth_client):
        resp = auth_client.get('/login')
        assert resp.status_code == 302
        assert '/' in resp.location

    def test_login_success_redirects_to_dashboard(self, client, user):
        resp = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword123',
        })
        assert resp.status_code == 302
        assert resp.location.endswith('/')

    def test_login_wrong_password_returns_200(self, client, user):
        resp = client.post('/login', data={
            'username': 'testuser',
            'password': 'wrong-password',
        })
        assert resp.status_code == 200

    def test_login_wrong_password_shows_error(self, client, user):
        resp = client.post('/login', data={
            'username': 'testuser',
            'password': 'wrong-password',
        })
        assert b'Invalid username or password' in resp.data

    def test_login_unknown_user_shows_error(self, client, user):
        resp = client.post('/login', data={
            'username': 'nobody',
            'password': 'testpassword123',
        })
        assert b'Invalid username or password' in resp.data

    def test_login_empty_username_fails_validation(self, client, user):
        resp = client.post('/login', data={
            'username': '',
            'password': 'testpassword123',
        })
        assert resp.status_code == 200  # re-renders form

    def test_login_next_param_used_for_safe_redirect(self, client, user):
        resp = client.post('/login?next=%2Fbig-ideas%2F', data={
            'username': 'testuser',
            'password': 'testpassword123',
        })
        assert resp.status_code == 302
        assert '/big-ideas/' in resp.location

    def test_open_redirect_via_next_param_is_blocked(self, client, user):
        """External URL in next= must be ignored to prevent open redirect."""
        resp = client.post('/login?next=http%3A%2F%2Fevil.com', data={
            'username': 'testuser',
            'password': 'testpassword123',
        })
        assert resp.status_code == 302
        assert 'evil.com' not in resp.location


class TestLogout:
    def test_logout_redirects_to_login(self, auth_client):
        resp = auth_client.post('/logout')
        assert resp.status_code == 302
        assert '/login' in resp.location

    def test_after_logout_dashboard_requires_login(self, auth_client):
        auth_client.post('/logout')
        resp = auth_client.get('/', follow_redirects=False)
        assert resp.status_code == 302
        assert '/login' in resp.location

    def test_logout_requires_post(self, auth_client):
        """GET on /logout should 405 (method not allowed), not log out silently."""
        resp = auth_client.get('/logout')
        assert resp.status_code == 405


class TestProtectedRoutes:
    """All app routes (except /login) must redirect unauthenticated users."""

    PROTECTED_GETS = [
        '/',
        '/mind-dump/',
        '/big-ideas/',
        '/big-ideas/new',
        '/projects/',
        '/projects/new',
        '/tasks/new',
    ]

    @pytest.mark.parametrize('path', PROTECTED_GETS)
    def test_unauthenticated_get_redirects_to_login(self, client, path):
        resp = client.get(path)
        assert resp.status_code == 302
        assert '/login' in resp.location


class TestSessionInactivity:
    def test_expired_session_redirects_to_login(self, client, user):
        """Simulate a session whose last_activity timestamp is very old."""
        # First log in
        client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword123',
        })
        # Wind back last_activity to simulate 2 hours ago
        with client.session_transaction() as sess:
            sess['_last_activity'] = time.time() - 7201  # >60 min

        resp = client.get('/', follow_redirects=False)
        assert resp.status_code == 302
        assert '/login' in resp.location

    def test_recent_activity_keeps_session_alive(self, auth_client):
        """A fresh session should pass the inactivity check."""
        resp = auth_client.get('/', follow_redirects=False)
        assert resp.status_code == 200
