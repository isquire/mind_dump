"""
Unit tests for SQLAlchemy models.
No HTTP requests — tests model methods and properties directly.
"""
import pytest
from datetime import date, timedelta
from models import User, BigIdea, Project, Task, MindDump


class TestUser:
    def test_password_not_stored_in_plaintext(self, db):
        u = User(username='alice')
        u.set_password('secret123')
        assert u.password_hash != 'secret123'

    def test_password_hash_starts_with_bcrypt_prefix(self, db):
        u = User(username='alice')
        u.set_password('secret123')
        # bcrypt hashes always start with $2b$
        assert u.password_hash.startswith('$2b$')

    def test_correct_password_returns_true(self, db):
        u = User(username='alice')
        u.set_password('correct-password')
        assert u.check_password('correct-password') is True

    def test_wrong_password_returns_false(self, db):
        u = User(username='alice')
        u.set_password('correct-password')
        assert u.check_password('wrong-password') is False

    def test_empty_password_returns_false(self, db):
        u = User(username='alice')
        u.set_password('correct-password')
        assert u.check_password('') is False

    def test_two_hashes_of_same_password_differ(self, db):
        """bcrypt salts ensure identical passwords produce different hashes."""
        u1, u2 = User(username='a'), User(username='b')
        u1.set_password('same'), u2.set_password('same')
        assert u1.password_hash != u2.password_hash


class TestBigIdea:
    def test_total_tasks_empty(self, db, big_idea):
        assert big_idea.total_tasks == 0

    def test_total_tasks_counts_across_projects(self, db, big_idea):
        p1 = Project(big_idea_id=big_idea.id, title='P1')
        p2 = Project(big_idea_id=big_idea.id, title='P2')
        db.session.add_all([p1, p2])
        db.session.flush()
        db.session.add_all([
            Task(project_id=p1.id, title='T1'),
            Task(project_id=p1.id, title='T2'),
            Task(project_id=p2.id, title='T3'),
        ])
        db.session.commit()
        db.session.expire_all()
        assert big_idea.total_tasks == 3

    def test_done_tasks_counts_only_done(self, db, big_idea):
        p = Project(big_idea_id=big_idea.id, title='P')
        db.session.add(p)
        db.session.flush()
        db.session.add_all([
            Task(project_id=p.id, title='T1', status='Done'),
            Task(project_id=p.id, title='T2', status='In Progress'),
            Task(project_id=p.id, title='T3', status='Done'),
        ])
        db.session.commit()
        db.session.expire_all()
        assert big_idea.done_tasks == 2


class TestProject:
    def test_completion_percentage_no_tasks(self, db, project):
        assert project.completion_percentage == 0

    def test_completion_percentage_none_done(self, db, project):
        db.session.add_all([
            Task(project_id=project.id, title='T1', status='Not Started'),
            Task(project_id=project.id, title='T2', status='In Progress'),
        ])
        db.session.commit()
        db.session.expire_all()
        assert project.completion_percentage == 0

    def test_completion_percentage_half_done(self, db, project):
        db.session.add_all([
            Task(project_id=project.id, title='T1', status='Done'),
            Task(project_id=project.id, title='T2', status='Not Started'),
        ])
        db.session.commit()
        db.session.expire_all()
        assert project.completion_percentage == 50

    def test_completion_percentage_all_done(self, db, project):
        db.session.add_all([
            Task(project_id=project.id, title='T1', status='Done'),
            Task(project_id=project.id, title='T2', status='Done'),
        ])
        db.session.commit()
        db.session.expire_all()
        assert project.completion_percentage == 100

    def test_done_tasks_property(self, db, project):
        db.session.add_all([
            Task(project_id=project.id, title='T1', status='Done'),
            Task(project_id=project.id, title='T2', status='Not Started'),
            Task(project_id=project.id, title='T3', status='Done'),
        ])
        db.session.commit()
        db.session.expire_all()
        assert project.done_tasks == 2

    def test_is_overdue_past_due_not_done(self, db, project):
        project.due_date = date.today() - timedelta(days=1)
        project.completion_percentage  # dummy access
        # completion_percentage is 0 (no tasks), so < 100
        db.session.commit()
        db.session.expire_all()
        assert project.is_overdue is True

    def test_is_overdue_future_date(self, db, project):
        project.due_date = date.today() + timedelta(days=7)
        db.session.commit()
        db.session.expire_all()
        assert project.is_overdue is False

    def test_is_overdue_no_due_date(self, db, project):
        assert project.is_overdue is False


class TestTask:
    def test_is_overdue_past_date_not_done(self, db, project):
        t = Task(
            project_id=project.id,
            title='Old task',
            due_date=date.today() - timedelta(days=1),
            status='Not Started',
        )
        assert t.is_overdue is True

    def test_is_overdue_false_when_done(self, db, project):
        t = Task(
            project_id=project.id,
            title='Done task',
            due_date=date.today() - timedelta(days=1),
            status='Done',
        )
        assert t.is_overdue is False

    def test_is_overdue_false_future_date(self, db, project):
        t = Task(
            project_id=project.id,
            title='Future task',
            due_date=date.today() + timedelta(days=3),
            status='Not Started',
        )
        assert t.is_overdue is False

    def test_is_overdue_false_no_due_date(self, db, project):
        t = Task(project_id=project.id, title='No date')
        assert t.is_overdue is False

    def test_status_badge_not_started(self, db, project):
        t = Task(project_id=project.id, title='T', status='Not Started')
        assert t.status_badge_class == 'bg-secondary'

    def test_status_badge_in_progress(self, db, project):
        t = Task(project_id=project.id, title='T', status='In Progress')
        assert t.status_badge_class == 'bg-primary'

    def test_status_badge_done(self, db, project):
        t = Task(project_id=project.id, title='T', status='Done')
        assert t.status_badge_class == 'bg-success'

    def test_status_badge_blocked(self, db, project):
        t = Task(project_id=project.id, title='T', status='Blocked')
        assert t.status_badge_class == 'bg-warning text-dark'

    def test_default_status_is_not_started(self, db, project):
        t = Task(project_id=project.id, title='T')
        db.session.add(t)
        db.session.commit()
        assert t.status == 'Not Started'

    def test_default_is_pinned_false(self, db, project):
        t = Task(project_id=project.id, title='T')
        db.session.add(t)
        db.session.commit()
        assert t.is_pinned is False


class TestMindDump:
    def test_default_status_unorganized(self, db):
        entry = MindDump(content='test')
        db.session.add(entry)
        db.session.commit()
        assert entry.status == 'Unorganized'

    def test_created_at_set_automatically(self, db):
        entry = MindDump(content='test')
        db.session.add(entry)
        db.session.commit()
        assert entry.created_at is not None
