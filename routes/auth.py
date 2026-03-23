"""Authentication routes: login and logout."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user

from models import User
from forms.auth import LoginForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            session.permanent = True
            session['_last_activity'] = __import__('time').time()
            next_page = request.args.get('next')
            # Guard against open-redirect: only allow relative paths
            if next_page and not next_page.startswith('/'):
                next_page = None
            return redirect(next_page or url_for('dashboard.index'))
        flash('Invalid username or password.', 'danger')

    return render_template('login.html', form=form)


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
