"""
Mind Dump — ADHD productivity app.
Entry point: initialises Flask, extensions, blueprints, and security headers.
Run via run.sh (which sets FLASK_ENV=production and loads .env).
"""
import os
import getpass
from datetime import datetime, timedelta, timezone

from flask import Flask, redirect, url_for, flash, session
from flask_login import LoginManager, current_user, logout_user
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

from models import db, User, MindDump

load_dotenv()

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    app = Flask(__name__)

    # --- Configuration ------------------------------------------------------
    secret = os.environ.get('SECRET_KEY')
    if not secret:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set. "
            "Copy .env.example to .env and set a strong random value."
        )
    app.config['SECRET_KEY'] = secret
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///mind_dump.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Session expires after 60 minutes of inactivity (enforced in before_request)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600

    # --- Extensions ---------------------------------------------------------
    db.init_app(app)
    CSRFProtect(app)

    login_manager = LoginManager(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to continue.'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    # --- Inactivity timeout -------------------------------------------------
    @app.before_request
    def enforce_session_timeout():
        if current_user.is_authenticated:
            last = session.get('_last_activity')
            now = datetime.now(timezone.utc).timestamp()
            if last and (now - last) > 3600:
                logout_user()
                session.clear()
                flash('Your session expired due to inactivity.', 'info')
                return redirect(url_for('auth.login'))
            session['_last_activity'] = now
            session.permanent = True

    # --- Security headers ---------------------------------------------------
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # All assets are served from 'self'; Quill injects inline styles
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' data:"
        )
        return response

    # --- Context processor (nav badges + view preference) ------------------
    @app.context_processor
    def inject_nav_data():
        if current_user.is_authenticated:
            from sqlalchemy import func
            counts = (
                db.session.query(MindDump.category, func.count(MindDump.id))
                .filter(MindDump.status == 'Unorganized')
                .group_by(MindDump.category)
                .all()
            )
            count_map = dict(counts)
            work_count = count_map.get('work', 0)
            personal_count = count_map.get('personal', 0)
            view = current_user.view_preference or 'all'
            return {
                'unorganized_count': work_count + personal_count,
                'unorganized_work_count': work_count,
                'unorganized_personal_count': personal_count,
                'current_view': view,
            }
        return {
            'unorganized_count': 0,
            'unorganized_work_count': 0,
            'unorganized_personal_count': 0,
            'current_view': 'all',
        }

    # --- Blueprints ---------------------------------------------------------
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.focus import focus_bp
    from routes.mind_dump import mind_dump_bp
    from routes.big_ideas import big_ideas_bp
    from routes.projects import projects_bp
    from routes.tasks import tasks_bp
    from routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(focus_bp)
    app.register_blueprint(mind_dump_bp)
    app.register_blueprint(big_ideas_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(reports_bp)

    return app


# ---------------------------------------------------------------------------
# First-run setup: prompt for initial user via CLI if none exists
# ---------------------------------------------------------------------------

def _migrate_add_category_columns(engine) -> None:
    """Add category/view_preference columns if they don't exist (one-time migration)."""
    with engine.connect() as conn:
        from sqlalchemy import text
        migrations = [
            ("big_ideas", "category", "VARCHAR(10) NOT NULL DEFAULT 'work'"),
            ("projects", "category", "VARCHAR(10) NOT NULL DEFAULT 'work'"),
            ("tasks", "category", "VARCHAR(10) NOT NULL DEFAULT 'work'"),
            ("mind_dump", "category", "VARCHAR(10) NOT NULL DEFAULT 'work'"),
            ("users", "view_preference", "VARCHAR(10) NOT NULL DEFAULT 'all'"),
        ]
        for table, col, col_def in migrations:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            col_names = [r[1] for r in rows]
            if col not in col_names:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
        conn.commit()


def _migrate_nullable_project_id(engine) -> None:
    """Make tasks.project_id nullable if it isn't already (one-time migration)."""
    with engine.connect() as conn:
        from sqlalchemy import text
        rows = conn.execute(text("PRAGMA table_info(tasks)")).fetchall()
        col = next((r for r in rows if r[1] == 'project_id'), None)
        if col is None or col[3] == 0:
            return  # column missing or already nullable — nothing to do
        # SQLite doesn't support ALTER COLUMN; recreate the table
        conn.execute(text("PRAGMA foreign_keys = OFF"))
        conn.execute(text("""
            CREATE TABLE tasks_new (
                id INTEGER NOT NULL PRIMARY KEY,
                project_id INTEGER,
                title VARCHAR(200) NOT NULL,
                notes TEXT,
                status VARCHAR(20),
                due_date DATE,
                external_link VARCHAR(500),
                is_pinned BOOLEAN NOT NULL,
                created_at DATETIME,
                completed_at DATETIME,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        """))
        conn.execute(text("INSERT INTO tasks_new SELECT * FROM tasks"))
        conn.execute(text("DROP TABLE tasks"))
        conn.execute(text("ALTER TABLE tasks_new RENAME TO tasks"))
        conn.execute(text("PRAGMA foreign_keys = ON"))
        conn.commit()


def _migrate_add_position_columns(engine) -> None:
    """Add position column to tasks and big_ideas if missing (one-time migration)."""
    with engine.connect() as conn:
        from sqlalchemy import text
        for table in ('tasks', 'big_ideas'):
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            col_names = [r[1] for r in rows]
            if 'position' not in col_names:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN position INTEGER"))
        conn.commit()


def _migrate_add_adhd_fields(engine) -> None:
    """Add estimated_minutes and first_action to tasks if missing (one-time migration)."""
    with engine.connect() as conn:
        from sqlalchemy import text
        migrations = [
            ("tasks", "estimated_minutes", "INTEGER"),
            ("tasks", "first_action", "VARCHAR(500)"),
        ]
        for table, col, col_def in migrations:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            col_names = [r[1] for r in rows]
            if col not in col_names:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
        conn.commit()


def init_db(app: Flask) -> None:
    """Create tables and create first user interactively if needed."""
    with app.app_context():
        db.create_all()
        _migrate_nullable_project_id(db.engine)
        _migrate_add_category_columns(db.engine)
        _migrate_add_adhd_fields(db.engine)
        _migrate_add_position_columns(db.engine)

        if User.query.count() == 0:
            print("\n=== First Run Setup ===")
            print("No user account found. Let's create one now.\n")

            username = input("Username: ").strip()
            while not username:
                username = input("  Username cannot be empty. Username: ").strip()

            password = getpass.getpass("Password (min 8 chars): ")
            while len(password) < 8:
                password = getpass.getpass(
                    "  Password must be at least 8 characters. Password: "
                )

            confirm = getpass.getpass("Confirm password: ")
            while password != confirm:
                print("  Passwords do not match, try again.")
                password = getpass.getpass("Password: ")
                while len(password) < 8:
                    password = getpass.getpass(
                        "  Password must be at least 8 characters. Password: "
                    )
                confirm = getpass.getpass("Confirm password: ")

            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            print(f"\nAccount '{username}' created. You can now log in.\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    application = create_app()
    init_db(application)
    # debug=False is enforced; run.sh also sets FLASK_ENV=production
    application.run(host='0.0.0.0', port=5000, debug=False)
