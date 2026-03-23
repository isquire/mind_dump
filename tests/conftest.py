"""
Shared pytest fixtures for Mind Dump tests.

Each test gets a fresh function-scoped Flask app backed by an in-memory
SQLite database. StaticPool ensures all connections (test code + request
handlers) share the same in-memory database so commits are visible across
the request boundary without needing a file on disk.
"""
import os

# Set required env vars BEFORE importing the app (create_app raises without them)
os.environ['SECRET_KEY'] = 'test-secret-key-for-pytest-only'

import pytest
from datetime import date, timedelta
from sqlalchemy.pool import StaticPool

from app import create_app
from models import db as _db, User, BigIdea, Project, Task, MindDump


# ── App / client ─────────────────────────────────────────────────────────────

@pytest.fixture()
def app():
    """Function-scoped Flask app; fresh in-memory DB per test."""
    flask_app = create_app()
    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,   # disabled for most tests; see csrf_app below
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        },
    })
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    """SQLAlchemy db handle — app context already active from `app` fixture."""
    return _db


# ── Domain object factories ───────────────────────────────────────────────────

@pytest.fixture()
def user(db):
    u = User(username='testuser')
    u.set_password('testpassword123')
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture()
def big_idea(db):
    idea = BigIdea(title='Test Idea', accent_color='#6366f1')
    db.session.add(idea)
    db.session.commit()
    return idea


@pytest.fixture()
def project(db, big_idea):
    p = Project(big_idea_id=big_idea.id, title='Test Project')
    db.session.add(p)
    db.session.commit()
    return p


@pytest.fixture()
def task(db, project):
    t = Task(project_id=project.id, title='Test Task')
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture()
def overdue_task(db, project):
    t = Task(
        project_id=project.id,
        title='Overdue Task',
        due_date=date.today() - timedelta(days=3),
        status='Not Started',
    )
    db.session.add(t)
    db.session.commit()
    return t


@pytest.fixture()
def mind_dump_entry(db):
    entry = MindDump(content='Something on my mind')
    db.session.add(entry)
    db.session.commit()
    return entry


# ── Authenticated client ──────────────────────────────────────────────────────

@pytest.fixture()
def auth_client(client, user):
    """Test client pre-logged-in as testuser."""
    resp = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpassword123',
    })
    assert resp.status_code == 302, (
        f"Login fixture failed (status {resp.status_code}). "
        f"Check that WTF_CSRF_ENABLED=False is applied."
    )
    return client


# ── CSRF-enabled app (security tests only) ───────────────────────────────────

@pytest.fixture()
def csrf_app():
    """Separate app instance with CSRF protection ENABLED."""
    flask_app = create_app()
    flask_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': True,
        'WTF_CSRF_CHECK_DEFAULT': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        },
    })
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def csrf_client(csrf_app):
    return csrf_app.test_client()
