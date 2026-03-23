"""
SQLAlchemy models for Mind Dump productivity app.
All database access goes through these ORM models — no raw SQL.
"""
from datetime import datetime, timezone, date as date_type
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import bcrypt

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """Single-user authentication model."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password: str) -> None:
        """Hash and store password using bcrypt."""
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.password_hash = hashed.decode('utf-8')

    def check_password(self, password: str) -> bool:
        """Verify a plaintext password against stored bcrypt hash."""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )


class BigIdea(db.Model):
    """Top-level organiser — a theme or goal that projects live under."""
    __tablename__ = 'big_ideas'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    accent_color = db.Column(db.String(7), default='#6366f1')  # CSS hex color
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    projects = db.relationship(
        'Project', backref='big_idea', lazy=True, cascade='all, delete-orphan'
    )

    @property
    def total_tasks(self) -> int:
        return sum(len(p.tasks) for p in self.projects)

    @property
    def done_tasks(self) -> int:
        return sum(
            sum(1 for t in p.tasks if t.status == 'Done')
            for p in self.projects
        )


class Project(db.Model):
    """A concrete project that belongs to a Big Idea."""
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    big_idea_id = db.Column(db.Integer, db.ForeignKey('big_ideas.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    # Validated to start with http:// or https:// before saving
    external_link = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    tasks = db.relationship(
        'Task', backref='project', lazy=True, cascade='all, delete-orphan'
    )

    @property
    def done_tasks(self) -> int:
        return sum(1 for t in self.tasks if t.status == 'Done')

    @property
    def completion_percentage(self) -> int:
        total = len(self.tasks)
        if total == 0:
            return 0
        return int((self.done_tasks / total) * 100)

    @property
    def is_overdue(self) -> bool:
        return bool(
            self.due_date and
            self.due_date < date_type.today() and
            self.completion_percentage < 100
        )


class Task(db.Model):
    """An actionable task within a project."""
    __tablename__ = 'tasks'

    STATUS_CHOICES = ['Not Started', 'In Progress', 'Done', 'Blocked']

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text)           # Rich text HTML from Quill
    status = db.Column(db.String(20), default='Not Started')
    due_date = db.Column(db.Date)
    # Validated to start with http:// or https:// before saving
    external_link = db.Column(db.String(500))
    # Only one task may be pinned as "My One Thing" at a time
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)

    mind_dump_entries = db.relationship(
        'MindDump',
        foreign_keys='MindDump.linked_task_id',
        backref='linked_task',
        lazy=True
    )

    @property
    def is_quick_task(self) -> bool:
        return self.project_id is None

    @property
    def is_overdue(self) -> bool:
        return bool(
            self.due_date and
            self.due_date < date_type.today() and
            self.status != 'Done'
        )

    @property
    def status_badge_class(self) -> str:
        """Bootstrap badge class for task status."""
        return {
            'Not Started': 'bg-secondary',
            'In Progress': 'bg-primary',
            'Done': 'bg-success',
            'Blocked': 'bg-warning text-dark',
        }.get(self.status, 'bg-secondary')


class MindDump(db.Model):
    """Quick-capture entries for thoughts, ideas, and to-dos."""
    __tablename__ = 'mind_dump'

    STATUS_CHOICES = ['Unorganized', 'Assigned', 'Someday']

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Unorganized')
    linked_task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)
    linked_project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    linked_big_idea_id = db.Column(db.Integer, db.ForeignKey('big_ideas.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    linked_project = db.relationship('Project', foreign_keys=[linked_project_id])
    linked_big_idea = db.relationship('BigIdea', foreign_keys=[linked_big_idea_id])
