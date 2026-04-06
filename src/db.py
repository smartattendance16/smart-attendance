"""
db.py — Database abstraction for Smart Attendance System
Uses PostgreSQL when DATABASE_URL is set (Render), SQLite otherwise (local).
"""

import os
import sqlite3

DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

USE_PG = bool(DATABASE_URL)

if USE_PG:
    import psycopg2
    import psycopg2.extras
    DBIntegrityError = psycopg2.IntegrityError
else:
    DBIntegrityError = sqlite3.IntegrityError


class _PGConnWrapper:
    """Wraps psycopg2 connection to accept ? placeholders like SQLite."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=None):
        sql = sql.replace('?', '%s')
        cur = self._conn.cursor()
        cur.execute(sql, params or ())
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_db(db_path=None):
    """Return a database connection."""
    if USE_PG:
        conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=psycopg2.extras.DictCursor,
        )
        return _PGConnWrapper(conn)
    if db_path is None:
        raise ValueError('db_path required for SQLite')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=None):
    """Create tables + seed default admin."""
    from werkzeug.security import generate_password_hash

    conn = get_db(db_path)

    if USE_PG:
        for stmt in [
            '''CREATE TABLE IF NOT EXISTS admin (
                id       SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email    TEXT DEFAULT '')''',
            '''CREATE TABLE IF NOT EXISTS otp_tokens (
                id         SERIAL PRIMARY KEY,
                username   TEXT NOT NULL,
                otp        TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used       INTEGER DEFAULT 0)''',
            '''CREATE TABLE IF NOT EXISTS students (
                id         SERIAL PRIMARY KEY,
                student_id TEXT UNIQUE NOT NULL,
                name       TEXT NOT NULL,
                email      TEXT DEFAULT '',
                department TEXT DEFAULT '',
                phone      TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''',
            '''CREATE TABLE IF NOT EXISTS attendance (
                id         SERIAL PRIMARY KEY,
                student_id TEXT NOT NULL,
                name       TEXT NOT NULL,
                date       DATE NOT NULL,
                time       TIME NOT NULL,
                status     TEXT DEFAULT 'Present')''',
            '''CREATE TABLE IF NOT EXISTS pending_students (
                id           SERIAL PRIMARY KEY,
                student_id   TEXT UNIQUE NOT NULL,
                name         TEXT NOT NULL,
                email        TEXT DEFAULT '',
                department   TEXT DEFAULT '',
                phone        TEXT DEFAULT '',
                photo_path   TEXT DEFAULT '',
                status       TEXT DEFAULT 'pending',
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at  TIMESTAMP,
                reviewed_by  TEXT DEFAULT '')''',
            '''CREATE TABLE IF NOT EXISTS face_encodings (
                id         SERIAL PRIMARY KEY,
                student_id TEXT NOT NULL,
                name       TEXT NOT NULL,
                encoding   BYTEA NOT NULL)''',
        ]:
            conn.execute(stmt)
        conn.execute(
            "INSERT INTO admin (username, password) VALUES (?, ?) "
            "ON CONFLICT (username) DO NOTHING",
            ('admin', generate_password_hash('admin123')),
        )
    else:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS admin (
                id       INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email    TEXT DEFAULT '');
            CREATE TABLE IF NOT EXISTS otp_tokens (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT NOT NULL,
                otp        TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used       INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS students (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                name       TEXT NOT NULL,
                email      TEXT DEFAULT '',
                department TEXT DEFAULT '',
                phone      TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS attendance (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                name       TEXT NOT NULL,
                date       DATE NOT NULL,
                time       TIME NOT NULL,
                status     TEXT DEFAULT 'Present');
            CREATE TABLE IF NOT EXISTS pending_students (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id   TEXT UNIQUE NOT NULL,
                name         TEXT NOT NULL,
                email        TEXT DEFAULT '',
                department   TEXT DEFAULT '',
                phone        TEXT DEFAULT '',
                photo_path   TEXT DEFAULT '',
                status       TEXT DEFAULT 'pending',
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at  TIMESTAMP,
                reviewed_by  TEXT DEFAULT '');
            CREATE TABLE IF NOT EXISTS face_encodings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                name       TEXT NOT NULL,
                encoding   BLOB NOT NULL);
        ''')
        conn.execute(
            "INSERT OR IGNORE INTO admin (username,password) VALUES (?,?)",
            ('admin', generate_password_hash('admin123')),
        )
        # Migration: add email column if missing
        cols = [r[1] for r in conn.execute('PRAGMA table_info(admin)').fetchall()]
        if 'email' not in cols:
            conn.execute('ALTER TABLE admin ADD COLUMN email TEXT DEFAULT ""')

    conn.commit()
    conn.close()
