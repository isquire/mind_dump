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

from models import db, User

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

    # --- Context processor (nav badges) ------------------------------------
    @app.context_processor
    def inject_nav_data():
        if current_user.is_authenticated:
            from models import MindDump
            count = MindDump.query.filter_by(status='Unorganized').count()
            return {'unorganized_count': count}
        return {'unorganized_count': 0}

    # --- Blueprints ---------------------------------------------------------
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.focus import focus_bp
    from routes.mind_dump import mind_dump_bp
    from routes.big_ideas import big_ideas_bp
    from routes.projects import projects_bp
    from routes.tasks import tasks_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(focus_bp)
    app.register_blueprint(mind_dump_bp)
    app.register_blueprint(big_ideas_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)

    return app


# ---------------------------------------------------------------------------
# First-run setup: prompt for initial user via CLI if none exists
# ---------------------------------------------------------------------------

def init_db(app: Flask) -> None:
    """Create tables and create first user interactively if needed."""
    with app.app_context():
        db.create_all()

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
