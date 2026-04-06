"""
wsgi.py — Production WSGI entry point for Smart Attendance System
Used by gunicorn / Render / any WSGI server.
"""

import os
import sys

# Add src/ to Python path
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, SRC_DIR)

from app import app, init_db

# Initialize the database on startup
init_db()

if __name__ == '__main__':
    app.run()
