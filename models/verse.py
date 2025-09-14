"""
Verse and verse-related models
"""
import sqlite3
from flask import current_app
from datetime import datetime

class Verse:
    def __init__(self, id, reference, text, translation='NIV', book=None, chapter=None,
                 verse_start=None, verse_end=None, difficulty_level=1, word_count=None):
        self.id = id
        self.reference = reference
        self.text = text
        self.translation = translation
        self.book = book
        self.chapter = chapter
        self.verse_start = verse_start
        self.verse_end = verse_end
        self.difficulty_level = difficulty_level
        self.word_count = word_count or len(text.split())

    @staticmethod
    def get_all(active_only=True):
        """Get all verses"""
        db = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row

        where_clause = "WHERE is_active = 1" if active_only else ""
        verses = db.execute(f'SELECT * FROM verses {where_clause} ORDER BY reference').fetchall()
        db.close()

        return [Verse(**dict(row)) for row in verses]

    @staticmethod
    def get_by_id(verse_id):
        """Get verse by ID"""
        db = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row
        verse_data = db.execute('SELECT * FROM verses WHERE id = ?', (verse_id,)).fetchone()
        db.close()

        if verse_data:
            return Verse(**dict(verse_data))
        return None

    @staticmethod
    def get_random():
        """Get a random verse"""
        db = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row
        verse_data = db.execute(
            'SELECT * FROM verses WHERE is_active = 1 ORDER BY RANDOM() LIMIT 1'
        ).fetchone()
        db.close()

        if verse_data:
            return Verse(**dict(verse_data))
        return None

    @staticmethod
    def create(reference, text, translation='NIV', book=None, chapter=None,
               verse_start=None, verse_end=None, difficulty_level=1):
        """Create a new verse"""
        db = sqlite3.connect(current_app.config['DATABASE'])
        word_count = len(text.split())

        cursor = db.execute(
            '''INSERT INTO verses (reference, text, translation, book, chapter,
               verse_start, verse_end, difficulty_level, word_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (reference, text, translation, book, chapter, verse_start, verse_end,
             difficulty_level, word_count)
        )
        db.commit()
        verse_id = cursor.lastrowid
        db.close()

        return Verse.get_by_id(verse_id)

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'reference': self.reference,
            'text': self.text,
            'translation': self.translation,
            'book': self.book,
            'chapter': self.chapter,
            'verse_start': self.verse_start,
            'verse_end': self.verse_end,
            'difficulty_level': self.difficulty_level,
            'word_count': self.word_count
        }

class RecitationAttempt:
    def __init__(self, id=None, student_id=None, verse_id=None, assignment_id=None,
                 recitation=None, score=0, attempt_number=1, time_spent_seconds=None,
                 used_speech_recognition=False, is_passing=False, created_at=None):
        self.id = id
        self.student_id = student_id
        self.verse_id = verse_id
        self.assignment_id = assignment_id
        self.recitation = recitation
        self.score = score
        self.attempt_number = attempt_number
        self.time_spent_seconds = time_spent_seconds
        self.used_speech_recognition = used_speech_recognition
        self.is_passing = is_passing
        self.created_at = created_at

    @staticmethod
    def create(student_id, verse_id, recitation, score, attempt_number=1,
               assignment_id=None, time_spent_seconds=None, used_speech_recognition=False):
        """Create a new recitation attempt"""
        db = sqlite3.connect(current_app.config['DATABASE'])
        is_passing = score >= 90

        cursor = db.execute(
            '''INSERT INTO recitation_attempts (student_id, verse_id, assignment_id, recitation,
               score, attempt_number, time_spent_seconds, used_speech_recognition, is_passing)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (student_id, verse_id, assignment_id, recitation, score, attempt_number,
             time_spent_seconds, used_speech_recognition, is_passing)
        )
        db.commit()
        attempt_id = cursor.lastrowid
        db.close()

        # Update student progress
        StudentProgress.update_progress(student_id, verse_id, score, attempt_number, is_passing)

        return attempt_id

    @staticmethod
    def get_student_attempts(student_id, verse_id=None, limit=None):
        """Get attempts for a student, optionally filtered by verse"""
        db = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row

        query = '''SELECT ra.*, v.reference, v.text as verse_text
                   FROM recitation_attempts ra
                   JOIN verses v ON ra.verse_id = v.id
                   WHERE ra.student_id = ?'''
        params = [student_id]

        if verse_id:
            query += ' AND ra.verse_id = ?'
            params.append(verse_id)

        query += ' ORDER BY ra.created_at DESC'

        if limit:
            query += f' LIMIT {limit}'

        attempts = db.execute(query, params).fetchall()
        db.close()

        return [dict(row) for row in attempts]

class StudentProgress:
    @staticmethod
    def update_progress(student_id, verse_id, score, attempt_number, is_passing):
        """Update student progress after an attempt"""
        db = sqlite3.connect(current_app.config['DATABASE'])

        # Get current progress or create new record
        current = db.execute(
            'SELECT * FROM student_progress WHERE student_id = ? AND verse_id = ?',
            (student_id, verse_id)
        ).fetchone()

        if current:
            # Update existing record
            new_total = current['total_attempts'] + 1
            new_best = max(current['best_score'], score)
            new_avg = ((current['average_score'] or 0) * current['total_attempts'] + score) / new_total

            # Determine if now memorized
            if is_passing and not current['is_memorized']:
                first_memorized_at = datetime.now().isoformat()
            else:
                first_memorized_at = current['first_memorized_at']

            # Simple trend analysis
            if score > (current['latest_score'] or 0):
                trend = 'improving'
            elif score < (current['latest_score'] or 0):
                trend = 'declining'
            else:
                trend = 'stable'

            db.execute(
                '''UPDATE student_progress SET
                   total_attempts = ?, best_score = ?, latest_score = ?, is_memorized = ?,
                   first_memorized_at = ?, last_attempt_at = CURRENT_TIMESTAMP,
                   average_score = ?, improvement_trend = ?
                   WHERE student_id = ? AND verse_id = ?''',
                (new_total, new_best, score, is_passing, first_memorized_at,
                 new_avg, trend, student_id, verse_id)
            )
        else:
            # Create new progress record
            db.execute(
                '''INSERT INTO student_progress
                   (student_id, verse_id, total_attempts, best_score, latest_score,
                    is_memorized, first_memorized_at, last_attempt_at, average_score,
                    improvement_trend)
                   VALUES (?, ?, 1, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, 'stable')''',
                (student_id, verse_id, score, score, is_passing,
                 datetime.now().isoformat() if is_passing else None, score)
            )

        db.commit()
        db.close()

    @staticmethod
    def get_student_progress(student_id, verse_id=None):
        """Get progress for a student, optionally for specific verse"""
        db = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row

        query = '''SELECT sp.*, v.reference, v.text
                   FROM student_progress sp
                   JOIN verses v ON sp.verse_id = v.id
                   WHERE sp.student_id = ?'''
        params = [student_id]

        if verse_id:
            query += ' AND sp.verse_id = ?'
            params.append(verse_id)

        progress = db.execute(query, params).fetchall()
        db.close()

        return [dict(row) for row in progress]