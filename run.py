#!/usr/bin/env python3
"""
Development server runner for Bible Memorizer
"""
import os
from app import create_app

if __name__ == '__main__':
    app = create_app()

    # Initialize database on first run
    with app.app_context():
        from app import get_db
        import sqlite3

        try:
            db = get_db()
            # Test if tables exist
            db.execute('SELECT COUNT(*) FROM users LIMIT 1')
            db.close()
            print("Database already initialized.")
        except sqlite3.OperationalError:
            print("Initializing database...")
            from app import init_db
            init_db()
            print("Database initialized successfully!")

    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'

    app.run(host='0.0.0.0', port=port, debug=debug)