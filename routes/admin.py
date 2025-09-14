"""
Admin routes for teachers and administrators
"""
from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
import sqlite3
from flask import current_app
from models.user import User
from models.verse import Verse
from datetime import datetime, timedelta

bp = Blueprint('admin', __name__, url_prefix='/admin')

def get_db():
    db = sqlite3.connect(current_app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db

def require_teacher(f):
    """Decorator to require teacher/admin role"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_teacher():
            if request.is_json:
                return jsonify({'error': 'Teacher access required'}), 403
            flash('Teacher access required', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_admin(f):
    """Decorator to require admin role"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            if request.is_json:
                return jsonify({'error': 'Admin access required'}), 403
            flash('Admin access required', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# --- CLASS MANAGEMENT ---

@bp.route('/classes', methods=['GET', 'POST'])
@login_required
@require_teacher
def manage_classes():
    """Get or create classes"""
    if request.method == 'GET':
        db = get_db()
        classes = db.execute(
            '''SELECT c.*, COUNT(cm.student_id) as student_count
               FROM classes c
               LEFT JOIN class_memberships cm ON c.id = cm.class_id AND cm.is_active = 1
               WHERE c.teacher_id = ? AND c.is_active = 1
               GROUP BY c.id
               ORDER BY c.name''',
            (current_user.id,)
        ).fetchall()
        db.close()

        if request.is_json:
            return jsonify([dict(row) for row in classes])
        return render_template('admin/classes.html', classes=classes)

    # Create new class
    data = request.get_json() if request.is_json else request.form
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()

    if not name:
        error = 'Class name is required'
        if request.is_json:
            return jsonify({'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('admin.manage_classes'))

    db = get_db()
    cursor = db.execute(
        'INSERT INTO classes (name, description, teacher_id) VALUES (?, ?, ?)',
        (name, description, current_user.id)
    )
    db.commit()
    class_id = cursor.lastrowid
    db.close()

    if request.is_json:
        return jsonify({'success': True, 'class_id': class_id}), 201

    flash('Class created successfully', 'success')
    return redirect(url_for('admin.manage_classes'))

@bp.route('/classes/<int:class_id>/students', methods=['GET', 'POST', 'DELETE'])
@login_required
@require_teacher
def manage_class_students(class_id):
    """Manage students in a class"""
    db = get_db()

    # Verify teacher owns this class
    class_info = db.execute(
        'SELECT * FROM classes WHERE id = ? AND teacher_id = ?',
        (class_id, current_user.id)
    ).fetchone()

    if not class_info:
        db.close()
        if request.is_json:
            return jsonify({'error': 'Class not found'}), 404
        flash('Class not found', 'error')
        return redirect(url_for('admin.manage_classes'))

    if request.method == 'GET':
        # Get students in class
        students = db.execute(
            '''SELECT u.id, u.email, u.first_name, u.last_name, cm.joined_at
               FROM users u
               JOIN class_memberships cm ON u.id = cm.student_id
               WHERE cm.class_id = ? AND cm.is_active = 1 AND u.is_active = 1
               ORDER BY u.last_name, u.first_name''',
            (class_id,)
        ).fetchall()

        # Get available students not in class
        available_students = db.execute(
            '''SELECT u.id, u.email, u.first_name, u.last_name
               FROM users u
               WHERE u.role = 'student' AND u.is_active = 1
               AND u.id NOT IN (
                   SELECT cm.student_id FROM class_memberships cm
                   WHERE cm.class_id = ? AND cm.is_active = 1
               )
               ORDER BY u.last_name, u.first_name''',
            (class_id,)
        ).fetchall()

        db.close()

        if request.is_json:
            return jsonify({
                'class': dict(class_info),
                'students': [dict(row) for row in students],
                'available_students': [dict(row) for row in available_students]
            })

        return render_template('admin/class_students.html',
                             class_info=class_info,
                             students=students,
                             available_students=available_students)

    elif request.method == 'POST':
        # Add student to class
        data = request.get_json() if request.is_json else request.form
        student_id = data.get('student_id')

        if not student_id:
            db.close()
            error = 'Student ID is required'
            if request.is_json:
                return jsonify({'error': error}), 400
            flash(error, 'error')
            return redirect(url_for('admin.manage_class_students', class_id=class_id))

        # Check if student exists and is not already in class
        student = db.execute(
            'SELECT * FROM users WHERE id = ? AND role = "student" AND is_active = 1',
            (student_id,)
        ).fetchone()

        if not student:
            db.close()
            error = 'Student not found'
            if request.is_json:
                return jsonify({'error': error}), 404
            flash(error, 'error')
            return redirect(url_for('admin.manage_class_students', class_id=class_id))

        existing = db.execute(
            'SELECT * FROM class_memberships WHERE class_id = ? AND student_id = ? AND is_active = 1',
            (class_id, student_id)
        ).fetchone()

        if existing:
            db.close()
            error = 'Student is already in this class'
            if request.is_json:
                return jsonify({'error': error}), 409
            flash(error, 'error')
            return redirect(url_for('admin.manage_class_students', class_id=class_id))

        # Add student to class
        db.execute(
            'INSERT INTO class_memberships (class_id, student_id) VALUES (?, ?)',
            (class_id, student_id)
        )
        db.commit()
        db.close()

        if request.is_json:
            return jsonify({'success': True, 'message': 'Student added to class'})

        flash('Student added to class successfully', 'success')
        return redirect(url_for('admin.manage_class_students', class_id=class_id))

    elif request.method == 'DELETE':
        # Remove student from class
        data = request.get_json() if request.is_json else request.form
        student_id = data.get('student_id')

        if not student_id:
            db.close()
            if request.is_json:
                return jsonify({'error': 'Student ID is required'}), 400

        db.execute(
            'UPDATE class_memberships SET is_active = 0 WHERE class_id = ? AND student_id = ?',
            (class_id, student_id)
        )
        db.commit()
        db.close()

        if request.is_json:
            return jsonify({'success': True, 'message': 'Student removed from class'})

# --- VERSE MANAGEMENT ---

@bp.route('/verses', methods=['GET', 'POST'])
@login_required
@require_teacher
def manage_verses():
    """Get all verses or add new ones"""
    if request.method == 'GET':
        verses = Verse.get_all(active_only=False)
        if request.is_json:
            return jsonify([verse.to_dict() for verse in verses])
        return render_template('admin/verses.html', verses=verses)

    # Add new verse
    data = request.get_json() if request.is_json else request.form
    reference = data.get('reference', '').strip()
    text = data.get('text', '').strip()
    translation = data.get('translation', 'NIV').strip()
    difficulty_level = int(data.get('difficulty_level', 1))

    if not reference or not text:
        error = 'Reference and text are required'
        if request.is_json:
            return jsonify({'error': error}), 400
        flash(error, 'error')
        return redirect(url_for('admin.manage_verses'))

    # Parse reference for book, chapter, verses (simple parsing)
    import re
    match = re.match(r'^(.+?)\s+(\d+):(\d+)(?:-(\d+))?', reference)
    if match:
        book = match.group(1).strip()
        chapter = int(match.group(2))
        verse_start = int(match.group(3))
        verse_end = int(match.group(4)) if match.group(4) else None
    else:
        book = chapter = verse_start = verse_end = None

    verse = Verse.create(reference, text, translation, book, chapter, verse_start, verse_end, difficulty_level)

    if not verse:
        error = 'Failed to create verse (reference may already exist)'
        if request.is_json:
            return jsonify({'error': error}), 409
        flash(error, 'error')
        return redirect(url_for('admin.manage_verses'))

    if request.is_json:
        return jsonify({'success': True, 'verse': verse.to_dict()}), 201

    flash('Verse added successfully', 'success')
    return redirect(url_for('admin.manage_verses'))

# --- REPORTING ---

@bp.route('/reports/class-overview/<int:class_id>')
@login_required
@require_teacher
def class_overview_report(class_id):
    """Comprehensive class progress report"""
    db = get_db()

    # Verify teacher owns this class
    class_info = db.execute(
        'SELECT * FROM classes WHERE id = ? AND teacher_id = ?',
        (class_id, current_user.id)
    ).fetchone()

    if not class_info:
        db.close()
        if request.is_json:
            return jsonify({'error': 'Class not found'}), 404
        flash('Class not found', 'error')
        return redirect(url_for('admin.manage_classes'))

    # Get detailed student progress
    student_progress = db.execute(
        '''SELECT
           u.id, u.first_name, u.last_name,
           COUNT(DISTINCT sp.verse_id) as verses_attempted,
           COUNT(CASE WHEN sp.is_memorized = 1 THEN 1 END) as verses_memorized,
           AVG(sp.best_score) as avg_best_score,
           SUM(sp.total_attempts) as total_attempts,
           MAX(sp.last_attempt_at) as last_activity,
           COUNT(CASE WHEN sp.improvement_trend = 'improving' THEN 1 END) as improving_count,
           COUNT(CASE WHEN sp.improvement_trend = 'declining' THEN 1 END) as declining_count
           FROM users u
           JOIN class_memberships cm ON u.id = cm.student_id
           LEFT JOIN student_progress sp ON u.id = sp.student_id
           WHERE cm.class_id = ? AND cm.is_active = 1 AND u.is_active = 1
           GROUP BY u.id
           ORDER BY u.last_name, u.first_name''',
        (class_id,)
    ).fetchall()

    # Get class-wide verse difficulty analysis
    verse_difficulty = db.execute(
        '''SELECT
           v.reference, v.text, v.difficulty_level,
           COUNT(DISTINCT ra.student_id) as students_attempted,
           AVG(ra.score) as avg_score,
           COUNT(CASE WHEN ra.is_passing = 1 THEN 1 END) * 100.0 / COUNT(*) as pass_rate
           FROM verses v
           LEFT JOIN recitation_attempts ra ON v.id = ra.verse_id
           LEFT JOIN class_memberships cm ON ra.student_id = cm.student_id
           WHERE cm.class_id = ? AND cm.is_active = 1
           GROUP BY v.id
           HAVING students_attempted > 0
           ORDER BY avg_score ASC''',
        (class_id,)
    ).fetchall()

    # Get recent activity
    recent_activity = db.execute(
        '''SELECT
           u.first_name, u.last_name, v.reference, ra.score, ra.is_passing, ra.created_at
           FROM recitation_attempts ra
           JOIN users u ON ra.student_id = u.id
           JOIN verses v ON ra.verse_id = v.id
           JOIN class_memberships cm ON u.id = cm.student_id
           WHERE cm.class_id = ? AND cm.is_active = 1
           ORDER BY ra.created_at DESC
           LIMIT 50''',
        (class_id,)
    ).fetchall()

    db.close()

    report_data = {
        'class_info': dict(class_info),
        'student_progress': [dict(row) for row in student_progress],
        'verse_difficulty': [dict(row) for row in verse_difficulty],
        'recent_activity': [dict(row) for row in recent_activity],
        'generated_at': datetime.now().isoformat()
    }

    if request.is_json:
        return jsonify(report_data)

    return render_template('admin/class_report.html', **report_data)

@bp.route('/reports/student-detail/<int:student_id>')
@login_required
@require_teacher
def student_detail_report(student_id):
    """Detailed individual student report"""
    db = get_db()

    # Verify teacher has access to this student (through class membership)
    access_check = db.execute(
        '''SELECT DISTINCT u.*, c.name as class_name
           FROM users u
           JOIN class_memberships cm ON u.id = cm.student_id
           JOIN classes c ON cm.class_id = c.id
           WHERE u.id = ? AND c.teacher_id = ? AND cm.is_active = 1 AND u.is_active = 1''',
        (student_id, current_user.id)
    ).fetchone()

    if not access_check:
        db.close()
        if request.is_json:
            return jsonify({'error': 'Student not found or access denied'}), 404
        flash('Student not found or access denied', 'error')
        return redirect(url_for('admin.manage_classes'))

    # Get student progress over time
    progress_timeline = db.execute(
        '''SELECT
           DATE(ra.created_at) as date,
           v.reference,
           COUNT(*) as attempts,
           MAX(ra.score) as best_score,
           AVG(ra.score) as avg_score
           FROM recitation_attempts ra
           JOIN verses v ON ra.verse_id = v.id
           WHERE ra.student_id = ?
           GROUP BY DATE(ra.created_at), v.id
           ORDER BY date DESC
           LIMIT 30''',
        (student_id,)
    ).fetchall()

    # Get error patterns
    error_analysis = db.execute(
        '''SELECT
           re.error_type,
           COUNT(*) as count,
           GROUP_CONCAT(DISTINCT re.expected_word) as common_words
           FROM recitation_errors re
           JOIN recitation_attempts ra ON re.attempt_id = ra.id
           WHERE ra.student_id = ?
           GROUP BY re.error_type
           ORDER BY count DESC''',
        (student_id,)
    ).fetchall()

    # Get verse-specific performance
    verse_performance = db.execute(
        '''SELECT
           v.reference, v.text, v.difficulty_level,
           sp.total_attempts, sp.best_score, sp.is_memorized,
           sp.improvement_trend, sp.first_memorized_at, sp.last_attempt_at
           FROM student_progress sp
           JOIN verses v ON sp.verse_id = v.id
           WHERE sp.student_id = ?
           ORDER BY sp.last_attempt_at DESC''',
        (student_id,)
    ).fetchall()

    db.close()

    report_data = {
        'student': dict(access_check),
        'progress_timeline': [dict(row) for row in progress_timeline],
        'error_analysis': [dict(row) for row in error_analysis],
        'verse_performance': [dict(row) for row in verse_performance],
        'generated_at': datetime.now().isoformat()
    }

    if request.is_json:
        return jsonify(report_data)

    return render_template('admin/student_report.html', **report_data)

# --- DATA EXPORT ---

@bp.route('/export/class-data/<int:class_id>')
@login_required
@require_teacher
def export_class_data(class_id):
    """Export class data as CSV"""
    import csv
    import io
    from flask import make_response

    db = get_db()

    # Verify teacher owns this class
    class_info = db.execute(
        'SELECT * FROM classes WHERE id = ? AND teacher_id = ?',
        (class_id, current_user.id)
    ).fetchone()

    if not class_info:
        db.close()
        return jsonify({'error': 'Class not found'}), 404

    # Get comprehensive data
    data = db.execute(
        '''SELECT
           u.first_name, u.last_name, u.email,
           v.reference, ra.recitation, ra.score, ra.is_passing,
           ra.attempt_number, ra.created_at, ra.used_speech_recognition
           FROM recitation_attempts ra
           JOIN users u ON ra.student_id = u.id
           JOIN verses v ON ra.verse_id = v.id
           JOIN class_memberships cm ON u.id = cm.student_id
           WHERE cm.class_id = ? AND cm.is_active = 1
           ORDER BY u.last_name, u.first_name, ra.created_at''',
        (class_id,)
    ).fetchall()

    db.close()

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        'Student_First_Name', 'Student_Last_Name', 'Student_Email',
        'Verse_Reference', 'Recitation', 'Score', 'Passed',
        'Attempt_Number', 'Date_Time', 'Used_Speech_Recognition'
    ])

    # Data rows
    for row in data:
        writer.writerow([
            row['first_name'], row['last_name'], row['email'],
            row['reference'], row['recitation'], row['score'], row['is_passing'],
            row['attempt_number'], row['created_at'], row['used_speech_recognition']
        ])

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=class_{class_info["name"]}_data.csv'

    return response

# --- USER MANAGEMENT (Admin only) ---

@bp.route('/users', methods=['GET'])
@login_required
@require_admin
def manage_users():
    """Get all users for admin management"""
    db = get_db()
    users = db.execute(
        'SELECT id, email, first_name, last_name, role, is_active, created_at FROM users ORDER BY created_at DESC'
    ).fetchall()
    db.close()

    if request.is_json:
        return jsonify([dict(row) for row in users])

    return render_template('admin/users.html', users=users)

@bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@require_admin
def toggle_user_active(user_id):
    """Toggle user active status"""
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if not user:
        db.close()
        if request.is_json:
            return jsonify({'error': 'User not found'}), 404

    new_status = not user['is_active']
    db.execute('UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
               (new_status, user_id))
    db.commit()
    db.close()

    message = f"User {'activated' if new_status else 'deactivated'}"

    if request.is_json:
        return jsonify({'success': True, 'message': message, 'is_active': new_status})

    flash(message, 'success')
    return redirect(url_for('admin.manage_users'))