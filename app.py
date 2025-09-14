"""
Bible Memorizer Flask Application
Main application factory and configuration
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

def create_app(config_name='development'):
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')
    app.config['DATABASE'] = os.path.join(app.instance_path, 'bible_memorizer.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Enable CORS for API endpoints
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return get_user_by_id(int(user_id))

    # Database helper functions
    def get_db():
        db = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
        return db

    def init_db():
        """Initialize the database with schema"""
        with app.app_context():
            db = get_db()
            with app.open_resource('schema.sql') as f:
                db.executescript(f.read().decode('utf8'))
            db.close()

    # Import and register blueprints
    from routes.auth import bp as auth_bp
    from routes.api import bp as api_bp
    from routes.admin import bp as admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    # Main routes
    @app.route('/')
    def index():
        """Serve the main application"""
        return render_template('index.html')

    @app.route('/admin-dashboard')
    @login_required
    def admin_dashboard():
        """Admin dashboard for teachers"""
        if current_user.role not in ['teacher', 'admin']:
            return redirect(url_for('index'))
        return render_template('admin_dashboard.html')

    @app.route('/student-dashboard')
    @login_required
    def student_dashboard():
        """Student progress dashboard"""
        return render_template('student_dashboard.html')

    # Initialize database helper
    def init_db_if_needed():
        """Initialize database if it doesn't exist"""
        import os
        if not os.path.exists(app.config['DATABASE']):
            init_db()

    # Make init function available
    app.init_db_if_needed = init_db_if_needed

    return app

def get_user_by_id(user_id):
    """Get user by ID for Flask-Login"""
    from models.user import User
    return User.get_by_id(user_id)

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)