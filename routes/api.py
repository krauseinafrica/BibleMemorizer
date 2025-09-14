"""
API Routes for Bible Memorizer
RESTful endpoints matching current Firebase operations
"""
from flask import Blueprint, request, jsonify, session, current_app
from flask_login import login_required, current_user
import sqlite3
from models.verse import Verse, RecitationAttempt, StudentProgress
from models.user import User
import re
from datetime import datetime

bp = Blueprint('api', __name__, url_prefix='/api')

def get_db():
    db = sqlite3.connect(current_app.config['DATABASE'])
    db.row_factory = sqlite3.Row
    return db

# --- VERSE ENDPOINTS ---

@bp.route('/verses', methods=['GET'])
def get_verses():
    """Get all available verses"""
    verses = Verse.get_all()
    return jsonify([verse.to_dict() for verse in verses])

@bp.route('/verses/random', methods=['GET'])
def get_random_verse():
    """Get a random verse for practice"""
    verse = Verse.get_random()
    if verse:
        return jsonify(verse.to_dict())
    return jsonify({'error': 'No verses available'}), 404

@bp.route('/verses/<int:verse_id>', methods=['GET'])
def get_verse(verse_id):
    """Get specific verse by ID"""
    verse = Verse.get_by_id(verse_id)
    if verse:
        return jsonify(verse.to_dict())
    return jsonify({'error': 'Verse not found'}), 404

# --- RECITATION ENDPOINTS ---

@bp.route('/recitations', methods=['POST'])
def submit_recitation():
    """
    Submit a recitation attempt
    Matches the current Firebase saveRecitationResult function
    """
    data = request.get_json()

    # Validate required fields
    required_fields = ['verseId', 'recitation', 'score']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    # For backward compatibility with frontend
    student_name = data.get('studentName', 'Anonymous')
    user_id = None

    # If user is logged in, use their info
    if current_user and current_user.is_authenticated:
        user_id = current_user.id
        student_name = current_user.full_name
    else:
        # For anonymous users, try to maintain session consistency
        if 'anonymous_user_id' not in session:
            # Create a temporary anonymous user record
            db = get_db()
            cursor = db.execute(
                'INSERT INTO users (email, password_hash, first_name, last_name, role) VALUES (?, ?, ?, ?, ?)',
                (f'anonymous_{datetime.now().timestamp()}@temp.com', 'anonymous', student_name, '', 'student')
            )
            db.commit()
            session['anonymous_user_id'] = cursor.lastrowid
            db.close()

        user_id = session['anonymous_user_id']

    # Get current attempt number for this verse
    attempts = RecitationAttempt.get_student_attempts(user_id, data['verseId'])
    attempt_number = len(attempts) + 1

    # Create the attempt record
    attempt_id = RecitationAttempt.create(
        student_id=user_id,
        verse_id=data['verseId'],
        recitation=data['recitation'],
        score=data['score'],
        attempt_number=attempt_number,
        assignment_id=data.get('assignmentId'),
        time_spent_seconds=data.get('timeSpentSeconds'),
        used_speech_recognition=data.get('usedSpeechRecognition', False)
    )

    # Process error analysis if diff data provided
    if 'diff' in data and attempt_id:
        process_recitation_errors(attempt_id, data['recitation'], data.get('correctAnswer', ''))

    return jsonify({
        'success': True,
        'attemptId': attempt_id,
        'message': 'Recitation saved successfully'
    })

def process_recitation_errors(attempt_id, user_text, correct_text):
    """Process and store detailed error analysis"""
    if not correct_text:
        return

    # Simple error detection - could be enhanced with more sophisticated NLP
    user_words = normalize_string(user_text).split()
    correct_words = normalize_string(correct_text).split()

    db = get_db()

    # Find missing words
    for i, correct_word in enumerate(correct_words):
        if i >= len(user_words) or user_words[i] != correct_word:
            # Determine error type
            if i >= len(user_words):
                error_type = 'missing_word'
                actual_word = None
            else:
                error_type = 'wrong_word'
                actual_word = user_words[i]

            # Get context
            context_before = ' '.join(correct_words[max(0, i-3):i])
            context_after = ' '.join(correct_words[i+1:min(len(correct_words), i+4)])

            db.execute(
                '''INSERT INTO recitation_errors
                   (attempt_id, error_type, position, expected_word, actual_word, context_before, context_after)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (attempt_id, error_type, i, correct_word, actual_word, context_before, context_after)
            )

    # Find extra words
    if len(user_words) > len(correct_words):
        for i in range(len(correct_words), len(user_words)):
            context_before = ' '.join(correct_words[max(0, len(correct_words)-3):])
            db.execute(
                '''INSERT INTO recitation_errors
                   (attempt_id, error_type, position, expected_word, actual_word, context_before, context_after)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (attempt_id, 'extra_word', i, None, user_words[i], context_before, '')
            )

    db.commit()
    db.close()

def normalize_string(text):
    """Normalize string for comparison (matches frontend logic)"""
    return re.sub(r'[.,\/#!$%\^&\*;:{}=\_`~()"\'""—?]', '', text.lower().strip()).replace('-', ' ').replace('  ', ' ')

# --- STUDENT PROGRESS ENDPOINTS ---

@bp.route('/progress/student/<int:student_id>', methods=['GET'])
@login_required
def get_student_progress(student_id):
    """Get progress for a specific student"""
    # Check authorization
    if not (current_user.is_teacher() or current_user.id == student_id):
        return jsonify({'error': 'Unauthorized'}), 403

    progress = StudentProgress.get_student_progress(student_id)
    return jsonify(progress)

@bp.route('/progress/my-progress', methods=['GET'])
def get_my_progress():
    """Get current user's progress (works for both logged in and anonymous users)"""
    user_id = None

    if current_user and current_user.is_authenticated:
        user_id = current_user.id
    elif 'anonymous_user_id' in session:
        user_id = session['anonymous_user_id']
    else:
        return jsonify({'progress': [], 'summary': {}})

    progress = StudentProgress.get_student_progress(user_id)

    # Calculate summary statistics
    if progress:
        total_verses = len(progress)
        memorized_count = sum(1 for p in progress if p['is_memorized'])
        avg_score = sum(p['best_score'] for p in progress) / total_verses if total_verses > 0 else 0
        total_attempts = sum(p['total_attempts'] for p in progress)

        summary = {
            'total_verses_attempted': total_verses,
            'verses_memorized': memorized_count,
            'average_best_score': round(avg_score, 1),
            'total_attempts': total_attempts,
            'completion_rate': round((memorized_count / total_verses) * 100, 1) if total_verses > 0 else 0
        }
    else:
        summary = {
            'total_verses_attempted': 0,
            'verses_memorized': 0,
            'average_best_score': 0,
            'total_attempts': 0,
            'completion_rate': 0
        }

    return jsonify({
        'progress': progress,
        'summary': summary
    })

@bp.route('/attempts/recent', methods=['GET'])
def get_recent_attempts():
    """Get recent attempts for current user"""
    user_id = None

    if current_user and current_user.is_authenticated:
        user_id = current_user.id
    elif 'anonymous_user_id' in session:
        user_id = session['anonymous_user_id']
    else:
        return jsonify([])

    limit = request.args.get('limit', 10, type=int)
    attempts = RecitationAttempt.get_student_attempts(user_id, limit=limit)

    return jsonify(attempts)

@bp.route('/attempts/verse/<int:verse_id>', methods=['GET'])
def get_verse_attempts(verse_id):
    """Get attempts for a specific verse by current user"""
    user_id = None

    if current_user and current_user.is_authenticated:
        user_id = current_user.id
    elif 'anonymous_user_id' in session:
        user_id = session['anonymous_user_id']
    else:
        return jsonify([])

    attempts = RecitationAttempt.get_student_attempts(user_id, verse_id=verse_id)
    return jsonify(attempts)

# --- ADMIN/TEACHER ENDPOINTS ---

@bp.route('/admin/students', methods=['GET'])
@login_required
def get_students():
    """Get all students (teacher/admin only)"""
    if not current_user.is_teacher():
        return jsonify({'error': 'Unauthorized'}), 403

    db = get_db()
    students = db.execute(
        '''SELECT id, email, first_name, last_name, created_at
           FROM users WHERE role = "student" AND is_active = 1
           ORDER BY last_name, first_name'''
    ).fetchall()
    db.close()

    return jsonify([dict(student) for student in students])

@bp.route('/admin/class-progress/<int:class_id>', methods=['GET'])
@login_required
def get_class_progress(class_id):
    """Get progress for all students in a class"""
    if not current_user.is_teacher():
        return jsonify({'error': 'Unauthorized'}), 403

    db = get_db()
    # Verify teacher owns this class
    class_info = db.execute(
        'SELECT * FROM classes WHERE id = ? AND teacher_id = ?',
        (class_id, current_user.id)
    ).fetchone()

    if not class_info:
        db.close()
        return jsonify({'error': 'Class not found or unauthorized'}), 404

    # Get all students in class with their progress
    progress_data = db.execute(
        '''SELECT u.id, u.first_name, u.last_name,
           COUNT(DISTINCT sp.verse_id) as verses_attempted,
           COUNT(CASE WHEN sp.is_memorized = 1 THEN 1 END) as verses_memorized,
           AVG(sp.best_score) as avg_score,
           SUM(sp.total_attempts) as total_attempts,
           MAX(sp.last_attempt_at) as last_activity
           FROM users u
           JOIN class_memberships cm ON u.id = cm.student_id
           LEFT JOIN student_progress sp ON u.id = sp.student_id
           WHERE cm.class_id = ? AND cm.is_active = 1 AND u.is_active = 1
           GROUP BY u.id, u.first_name, u.last_name
           ORDER BY u.last_name, u.first_name''',
        (class_id,)
    ).fetchall()
    db.close()

    return jsonify([dict(row) for row in progress_data])

# --- SETTINGS ENDPOINTS ---

@bp.route('/settings', methods=['GET'])
def get_settings():
    """Get application settings"""
    db = get_db()
    settings = db.execute('SELECT key, value FROM settings').fetchall()
    db.close()

    return jsonify({row['key']: row['value'] for row in settings})

@bp.route('/settings', methods=['POST'])
@login_required
def update_settings():
    """Update application settings (admin only)"""
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    db = get_db()

    for key, value in data.items():
        db.execute(
            'INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)',
            (key, str(value))
        )

    db.commit()
    db.close()

    return jsonify({'success': True, 'message': 'Settings updated'})

# --- ERROR ANALYSIS ENDPOINTS ---

@bp.route('/analysis/errors/<int:student_id>', methods=['GET'])
@login_required
def get_error_analysis(student_id):
    """Get detailed error analysis for a student"""
    # Check authorization
    if not (current_user.is_teacher() or current_user.id == student_id):
        return jsonify({'error': 'Unauthorized'}), 403

    db = get_db()

    # Get error patterns
    error_patterns = db.execute(
        '''SELECT error_type, COUNT(*) as count,
           GROUP_CONCAT(DISTINCT expected_word) as common_words
           FROM recitation_errors re
           JOIN recitation_attempts ra ON re.attempt_id = ra.id
           WHERE ra.student_id = ?
           GROUP BY error_type
           ORDER BY count DESC''',
        (student_id,)
    ).fetchall()

    # Get most problematic words
    problem_words = db.execute(
        '''SELECT expected_word, COUNT(*) as error_count,
           AVG(CASE WHEN actual_word IS NOT NULL THEN 1.0 ELSE 0.0 END) as substitution_rate
           FROM recitation_errors re
           JOIN recitation_attempts ra ON re.attempt_id = ra.id
           WHERE ra.student_id = ? AND expected_word IS NOT NULL
           GROUP BY expected_word
           HAVING error_count > 1
           ORDER BY error_count DESC
           LIMIT 20''',
        (student_id,)
    ).fetchall()

    db.close()

    return jsonify({
        'error_patterns': [dict(row) for row in error_patterns],
        'problem_words': [dict(row) for row in problem_words]
    })