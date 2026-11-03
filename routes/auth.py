import re
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import db
from models.user import User

auth_bp = Blueprint('auth', __name__)

EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


# ---------- Decorators ----------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('You do not have permission to access that page.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


# ---------- Routes ----------

@auth_bp.route('/')
def landing():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))
    return render_template('landing.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'worker')
        phone = request.form.get('phone', '').strip()

        errors = []
        if not full_name:
            errors.append('Full name is required.')
        if not email or not EMAIL_REGEX.match(email):
            errors.append('A valid email address is required.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if role not in ('admin', 'worker'):
            errors.append('Invalid role selected.')
        if email and User.query.filter_by(email=email).first():
            errors.append('An account with that email already exists.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('register.html', form=request.form)

        user = User(full_name=full_name, email=email, role=role, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html', form={})


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session.permanent = True
            session['user_id'] = user.id
            session['full_name'] = user.full_name
            session['role'] = user.role
            flash(f'Welcome back, {user.full_name}!', 'success')
            return redirect(url_for('dashboard.index'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    user = User.query.get_or_404(session['user_id'])
    return render_template('profile.html', user=user)
