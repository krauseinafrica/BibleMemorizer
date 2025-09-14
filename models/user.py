"""
User model for authentication and user management
"""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
from flask import current_app

class User(UserMixin):
    def __init__(self, id, email, password_hash, first_name, last_name, role='student', is_active=True):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.is_active = is_active

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_teacher(self):
        return self.role in ['teacher', 'admin']

    def is_admin(self):
        return self.role == 'admin'

    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        db = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row
        user_data = db.execute(
            'SELECT * FROM users WHERE id = ? AND is_active = 1', (user_id,)
        ).fetchone()
        db.close()

        if user_data:
            return User(
                id=user_data['id'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                role=user_data['role'],
                is_active=user_data['is_active']
            )
        return None

    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        db = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row
        user_data = db.execute(
            'SELECT * FROM users WHERE email = ? AND is_active = 1', (email,)
        ).fetchone()
        db.close()

        if user_data:
            return User(
                id=user_data['id'],
                email=user_data['email'],
                password_hash=user_data['password_hash'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                role=user_data['role'],
                is_active=user_data['is_active']
            )
        return None

    @staticmethod
    def create(email, password, first_name, last_name, role='student'):
        """Create a new user"""
        db = sqlite3.connect(current_app.config['DATABASE'])
        password_hash = generate_password_hash(password)

        try:
            cursor = db.execute(
                '''INSERT INTO users (email, password_hash, first_name, last_name, role)
                   VALUES (?, ?, ?, ?, ?)''',
                (email, password_hash, first_name, last_name, role)
            )
            db.commit()
            user_id = cursor.lastrowid
            db.close()

            return User.get_by_id(user_id)
        except sqlite3.IntegrityError:
            db.close()
            return None  # Email already exists

    def save(self):
        """Save user changes to database"""
        db = sqlite3.connect(current_app.config['DATABASE'])
        db.execute(
            '''UPDATE users SET email = ?, first_name = ?, last_name = ?,
               role = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?''',
            (self.email, self.first_name, self.last_name, self.role, self.is_active, self.id)
        )
        db.commit()
        db.close()

    def get_classes(self):
        """Get classes this user is in (students) or teaches (teachers)"""
        db = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row

        if self.role == 'student':
            classes = db.execute(
                '''SELECT c.* FROM classes c
                   JOIN class_memberships cm ON c.id = cm.class_id
                   WHERE cm.student_id = ? AND cm.is_active = 1 AND c.is_active = 1''',
                (self.id,)
            ).fetchall()
        else:  # teacher or admin
            classes = db.execute(
                'SELECT * FROM classes WHERE teacher_id = ? AND is_active = 1', (self.id,)
            ).fetchall()

        db.close()
        return [dict(row) for row in classes]

    def get_progress_summary(self):
        """Get student's overall progress summary"""
        if self.role != 'student':
            return None

        db = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row

        # Get overall stats
        stats = db.execute(
            '''SELECT
                COUNT(DISTINCT verse_id) as verses_attempted,
                COUNT(CASE WHEN is_memorized = 1 THEN 1 END) as verses_memorized,
                AVG(best_score) as average_best_score,
                SUM(total_attempts) as total_attempts
               FROM student_progress WHERE student_id = ?''',
            (self.id,)
        ).fetchone()

        # Get recent activity
        recent_attempts = db.execute(
            '''SELECT ra.*, v.reference, v.text
               FROM recitation_attempts ra
               JOIN verses v ON ra.verse_id = v.id
               WHERE ra.student_id = ?
               ORDER BY ra.created_at DESC LIMIT 10''',
            (self.id,)
        ).fetchall()

        db.close()

        return {
            'stats': dict(stats) if stats else {},
            'recent_attempts': [dict(row) for row in recent_attempts]
        }