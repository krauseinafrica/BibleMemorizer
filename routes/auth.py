"""
Authentication routes for user login, registration, and session management
"""
from flask import Blueprint, request, jsonify, session, redirect, url_for, flash, render_template
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from models.user import User
import re

bp = Blueprint('auth', __name__, url_prefix='/auth')

def validate_email(email):
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Basic password validation"""
    return len(password) >= 6

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'GET':
        return render_template('auth/login.html')

    data = request.get_json() if request.is_json else request.form
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        error = 'Email and password are required'
        if request.is_json:
            return jsonify({'error': error}), 400
        flash(error, 'error')
        return render_template('auth/login.html')

    user = User.get_by_email(email)
    if not user or not user.check_password(password):
        error = 'Invalid email or password'
        if request.is_json:
            return jsonify({'error': error}), 401
        flash(error, 'error')
        return render_template('auth/login.html')

    login_user(user, remember=True)

    # If there was an anonymous session, we could merge data here
    # For now, just clear the anonymous session
    session.pop('anonymous_user_id', None)

    if request.is_json:
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role
            }
        })

    # Redirect based on role
    if user.is_teacher():
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('student_dashboard'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'GET':
        return render_template('auth/register.html')

    data = request.get_json() if request.is_json else request.form
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    role = data.get('role', 'student').strip()

    # Validation
    errors = []
    if not email or not validate_email(email):
        errors.append('Valid email address is required')
    if not password or not validate_password(password):
        errors.append('Password must be at least 6 characters long')
    if not first_name:
        errors.append('First name is required')
    if not last_name:
        errors.append('Last name is required')
    if role not in ['student', 'teacher']:
        role = 'student'  # Default to student for security

    if errors:
        if request.is_json:
            return jsonify({'errors': errors}), 400
        for error in errors:
            flash(error, 'error')
        return render_template('auth/register.html')

    # Create user
    user = User.create(email, password, first_name, last_name, role)
    if not user:
        error = 'An account with this email already exists'
        if request.is_json:
            return jsonify({'error': error}), 409
        flash(error, 'error')
        return render_template('auth/register.html')

    # Auto-login the new user
    login_user(user)

    if request.is_json:
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role
            }
        }), 201

    flash('Account created successfully! Welcome!', 'success')
    if user.is_teacher():
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('student_dashboard'))

@bp.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    """User logout"""
    logout_user()
    session.clear()

    if request.is_json:
        return jsonify({'success': True, 'message': 'Logged out successfully'})

    flash('You have been logged out successfully', 'info')
    return redirect(url_for('index'))

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """View and update user profile"""
    if request.method == 'GET':
        if request.is_json:
            return jsonify({
                'id': current_user.id,
                'email': current_user.email,
                'first_name': current_user.first_name,
                'last_name': current_user.last_name,
                'full_name': current_user.full_name,
                'role': current_user.role
            })
        return render_template('auth/profile.html')

    # Update profile
    data = request.get_json() if request.is_json else request.form
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()

    errors = []
    if not first_name:
        errors.append('First name is required')
    if not last_name:
        errors.append('Last name is required')

    if errors:
        if request.is_json:
            return jsonify({'errors': errors}), 400
        for error in errors:
            flash(error, 'error')
        return render_template('auth/profile.html')

    # Update user
    current_user.first_name = first_name
    current_user.last_name = last_name
    current_user.save()

    if request.is_json:
        return jsonify({'success': True, 'message': 'Profile updated successfully'})

    flash('Profile updated successfully', 'success')
    return render_template('auth/profile.html')

@bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    data = request.get_json() if request.is_json else request.form
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    errors = []
    if not current_user.check_password(current_password):
        errors.append('Current password is incorrect')
    if not new_password or not validate_password(new_password):
        errors.append('New password must be at least 6 characters long')
    if new_password != confirm_password:
        errors.append('New passwords do not match')

    if errors:
        if request.is_json:
            return jsonify({'errors': errors}), 400
        for error in errors:
            flash(error, 'error')
        return redirect(url_for('auth.profile'))

    # Update password
    from werkzeug.security import generate_password_hash
    current_user.password_hash = generate_password_hash(new_password)
    current_user.save()

    if request.is_json:
        return jsonify({'success': True, 'message': 'Password changed successfully'})

    flash('Password changed successfully', 'success')
    return redirect(url_for('auth.profile'))

@bp.route('/current-user', methods=['GET'])
def current_user_info():
    """Get current user info (for frontend state management)"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'email': current_user.email,
                'first_name': current_user.first_name,
                'last_name': current_user.last_name,
                'full_name': current_user.full_name,
                'role': current_user.role
            }
        })
    else:
        # Check for anonymous session
        anonymous_id = session.get('anonymous_user_id')
        return jsonify({
            'authenticated': False,
            'anonymous_id': anonymous_id
        })

# Quick anonymous user setup for backward compatibility
@bp.route('/anonymous-session', methods=['POST'])
def create_anonymous_session():
    """Create anonymous session for guest users"""
    data = request.get_json() if request.is_json else request.form
    name = data.get('name', 'Anonymous').strip()

    if 'anonymous_user_id' not in session:
        from datetime import datetime
        import sqlite3
        from flask import current_app

        # Create temporary anonymous user
        db = sqlite3.connect(current_app.config['DATABASE'])
        cursor = db.execute(
            'INSERT INTO users (email, password_hash, first_name, last_name, role) VALUES (?, ?, ?, ?, ?)',
            (f'anonymous_{datetime.now().timestamp()}@temp.com', 'anonymous', name, '', 'student')
        )
        db.commit()
        session['anonymous_user_id'] = cursor.lastrowid
        session['anonymous_name'] = name
        db.close()

    return jsonify({
        'success': True,
        'anonymous_id': session['anonymous_user_id'],
        'name': session.get('anonymous_name', name)
    })