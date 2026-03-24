"""
Security tests: HTTP headers, CSRF protection, URL validation,
input sanitisation, and password storage.
"""
import re
import pytest
from models import User, Task, Project, BigIdea


REQUIRED_HEADERS = {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
}


class TestSecurityHeaders:
    """All responses must carry the required security headers."""

    def test_headers_on_login_page(self, client):
        resp = client.get('/login')
        for header, value in REQUIRED_HEADERS.items():
            assert resp.headers.get(header) == value, (
                f"Missing or wrong {header}: got {resp.headers.get(header)!r}"
            )

    def test_csp_header_present_on_login_page(self, client):
        resp = client.get('/login')
        csp = resp.headers.get('Content-Security-Policy', '')
        assert "default-src 'self'" in csp

    def test_headers_on_authenticated_page(self, auth_client):
        resp = auth_client.get('/')
        for header, value in REQUIRED_HEADERS.items():
            assert resp.headers.get(header) == value

    def test_x_frame_options_deny(self, client):
        resp = client.get('/login')
        assert resp.headers.get('X-Frame-Options') == 'DENY'

    def test_nosniff_header(self, client):
        resp = client.get('/login')
        assert resp.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_referrer_policy(self, client):
        resp = client.get('/login')
        assert resp.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'


class TestCSRFProtection:
    """CSRF protection must be active and block token-less POST requests."""

    def test_post_without_csrf_token_returns_400(self, csrf_client):
        """With CSRF enabled, POST without token should be rejected."""
        resp = csrf_client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword123',
        })
        assert resp.status_code == 400

    def test_post_with_valid_csrf_token_not_rejected_for_csrf(self, csrf_client):
        """With a valid CSRF token the request should proceed past CSRF check."""
        # GET the login page — this sets the CSRF cookie / session value
        get_resp = csrf_client.get('/login')
        # WTForms renders: id="csrf_token" name="csrf_token" type="hidden" value="..."
        # so we first find the full <input> tag, then extract its value= attribute
        tag_match = re.search(rb'<input[^>]+id="csrf_token"[^>]*>', get_resp.data)
        assert tag_match, "CSRF token input tag not found in login page HTML"
        val_match = re.search(rb'value="([^"]+)"', tag_match.group(0))
        assert val_match, "CSRF token value not found in input tag"
        token = val_match.group(1).decode()

        resp = csrf_client.post('/login', data={
            'username': 'nonexistent',
            'password': 'wrongpass',
            'csrf_token': token,
        })
        # CSRF check passed — returns 200 (re-render with "invalid creds" error)
        assert resp.status_code == 200
        assert b'Invalid username or password' in resp.data


class TestURLValidation:
    """external_link fields must only accept http:// or https:// URLs."""

    def test_project_rejects_ftp_url(self, auth_client, db, big_idea):
        resp = auth_client.post('/projects/new', data={
            'title': 'Bad Link Project',
            'big_idea_id': big_idea.id,
            'external_link': 'ftp://evil.example.com',
        })
        assert resp.status_code == 200  # re-renders with validation error
        assert Project.query.filter_by(title='Bad Link Project').first() is None

    def test_project_rejects_bare_string(self, auth_client, db, big_idea):
        resp = auth_client.post('/projects/new', data={
            'title': 'Bare String',
            'big_idea_id': big_idea.id,
            'external_link': 'not-a-url',
        })
        assert resp.status_code == 200
        assert Project.query.filter_by(title='Bare String').first() is None

    def test_project_accepts_https_url(self, auth_client, db, big_idea):
        resp = auth_client.post('/projects/new', data={
            'title': 'HTTPS Project',
            'big_idea_id': big_idea.id,
            'external_link': 'https://linear.app/board/123',
        })
        assert resp.status_code == 302
        p = Project.query.filter_by(title='HTTPS Project').first()
        assert p is not None
        assert p.external_link == 'https://linear.app/board/123'

    def test_project_accepts_http_url(self, auth_client, db, big_idea):
        resp = auth_client.post('/projects/new', data={
            'title': 'HTTP Project',
            'big_idea_id': big_idea.id,
            'external_link': 'http://localhost:8080/board',
        })
        assert resp.status_code == 302
        p = Project.query.filter_by(title='HTTP Project').first()
        assert p is not None

    def test_task_rejects_javascript_url(self, auth_client, db, project):
        resp = auth_client.post('/tasks/new', data={
            'title': 'JS URL Task',
            'project_id': project.id,
            'status': 'Not Started',
            'external_link': 'javascript:alert(1)',
        })
        assert resp.status_code == 200
        assert Task.query.filter_by(title='JS URL Task').first() is None

    def test_task_accepts_https_url(self, auth_client, db, project):
        resp = auth_client.post('/tasks/new', data={
            'title': 'Valid Link Task',
            'project_id': project.id,
            'status': 'Not Started',
            'external_link': 'https://trello.com/c/abc123',
        })
        assert resp.status_code == 302
        t = Task.query.filter_by(title='Valid Link Task').first()
        assert t is not None
        assert t.external_link == 'https://trello.com/c/abc123'


class TestHTMLSanitisation:
    """Quill notes HTML must be sanitised before saving to prevent XSS."""

    def test_script_tag_stripped_from_task_notes(self, auth_client, db, project):
        resp = auth_client.post('/tasks/new', data={
            'title': 'XSS Task',
            'project_id': project.id,
            'status': 'Not Started',
            'notes': '<script>alert("xss")</script><p>Safe content</p>',
        })
        assert resp.status_code == 302
        t = Task.query.filter_by(title='XSS Task').first()
        assert t is not None
        assert '<script>' not in (t.notes or '')
        assert 'Safe content' in (t.notes or '')

    def test_event_handler_stripped_from_task_notes(self, auth_client, db, project):
        resp = auth_client.post('/tasks/new', data={
            'title': 'Event Handler Task',
            'project_id': project.id,
            'status': 'Not Started',
            'notes': '<p onmouseover="evil()">hover me</p>',
        })
        assert resp.status_code == 302
        t = Task.query.filter_by(title='Event Handler Task').first()
        assert 'onmouseover' not in (t.notes or '')

    def test_allowed_html_tags_preserved(self, auth_client, db, project):
        resp = auth_client.post('/tasks/new', data={
            'title': 'Formatted Task',
            'project_id': project.id,
            'status': 'Not Started',
            'notes': '<p><strong>Bold</strong> and <em>italic</em></p>',
        })
        assert resp.status_code == 302
        t = Task.query.filter_by(title='Formatted Task').first()
        assert '<strong>' in (t.notes or '')
        assert '<em>' in (t.notes or '')


class TestPasswordStorage:
    def test_password_never_stored_in_plaintext(self, db):
        u = User(username='sectest')
        u.set_password('my-super-secret')
        db.session.add(u)
        db.session.commit()
        db.session.expire_all()
        stored = db.session.get(User, u.id)
        assert 'my-super-secret' not in stored.password_hash
        assert stored.password_hash.startswith('$2b$')


class TestOpenRedirect:
    """Referrer-based redirects must not send users to external sites."""

    def test_set_view_rejects_external_referer(self, auth_client):
        resp = auth_client.post(
            '/set-view',
            data={'view': 'work'},
            headers={'Referer': 'http://evil.example.com/phishing'},
        )
        assert resp.status_code == 302
        assert 'evil.example.com' not in resp.location

    def test_set_view_follows_local_referer(self, auth_client):
        resp = auth_client.post(
            '/set-view',
            data={'view': 'work'},
            headers={'Referer': 'http://localhost/big-ideas/'},
        )
        assert resp.status_code == 302
        assert '/big-ideas/' in resp.location

    def test_set_view_falls_back_to_dashboard_without_referer(self, auth_client):
        resp = auth_client.post('/set-view', data={'view': 'work'})
        assert resp.status_code == 302
        # Should land on dashboard index
        assert resp.location.endswith('/')

    def test_pin_rejects_external_referer(self, auth_client, task):
        resp = auth_client.post(
            f'/tasks/{task.id}/pin',
            headers={'Referer': 'http://evil.example.com/'},
        )
        assert resp.status_code == 302
        assert 'evil.example.com' not in resp.location

    def test_unpin_rejects_external_referer(self, auth_client, db, task):
        task.is_pinned = True
        db.session.commit()
        resp = auth_client.post(
            f'/tasks/{task.id}/unpin',
            headers={'Referer': 'http://evil.example.com/'},
        )
        assert resp.status_code == 302
        assert 'evil.example.com' not in resp.location

    def test_complete_rejects_external_referer(self, auth_client, task):
        resp = auth_client.post(
            f'/tasks/{task.id}/complete',
            headers={'Referer': 'http://evil.example.com/'},
        )
        assert resp.status_code == 302
        assert 'evil.example.com' not in resp.location
