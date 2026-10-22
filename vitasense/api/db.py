"""
VitaSense AI - Database Module (SQLite)
Manages SQLite connection, schema initialization, and thread-safe operations.
Supports per-user isolation, hashed session tokens, profiles, and measurements.
"""

import sqlite3
import os
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

DB_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DB_PATH = DB_DIR / "vitasense.db"


def get_db_path() -> Path:
    """Returns the database file path, ensuring parent directory exists."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    return DB_PATH


@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for SQLite database connection.
    Enforces foreign keys, row factory as Row, and auto-commit on exit.
    """
    db_file = get_db_path()
    conn = sqlite3.connect(str(db_file), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path = None) -> None:
    """
    Initializes database schema with tables:
    - users: authentication credentials & registration
    - user_profiles: clinical & demographic parameters
    - sessions: cryptographically hashed bearer tokens & expiration (FR-01, FR-13 hardening)
    - measurements: physiological time-series with quality flags & component checks
    - contact_messages: user support inquiries with rate-limiting support (FR-11)
    """
    if db_path is None:
        db_path = get_db_path()
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
    with conn:
        # Check if legacy sessions table with plaintext 'token' column exists
        cur = conn.execute("PRAGMA table_info(sessions);")
        columns = [row[1] for row in cur.fetchall()]
        if columns and "token" in columns and "token_hash" not in columns:
            conn.execute("DROP TABLE sessions;")

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                sex TEXT NOT NULL,
                height TEXT NOT NULL,
                weight TEXT NOT NULL,
                resting_hr INTEGER NOT NULL,
                activity_level TEXT NOT NULL,
                health_goal TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT 'email',
                updated_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT NOT NULL,
                trust_score REAL NOT NULL DEFAULT 1.0,
                quality_flags TEXT NOT NULL DEFAULT '[]',
                component_checks TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                ip_address TEXT
            );

            CREATE TABLE IF NOT EXISTS user_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'info',
                status TEXT NOT NULL DEFAULT 'active',
                reason TEXT NOT NULL DEFAULT '',
                recommended_step TEXT NOT NULL DEFAULT 'Monitor trends and consult a qualified healthcare professional if symptoms persist.',
                related_record_id INTEGER,
                created_at TEXT NOT NULL,
                acknowledged_at TEXT,
                dismissed_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (related_record_id) REFERENCES measurements(id) ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_measurements_user_ts 
                ON measurements(user_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_measurements_user_source 
                ON measurements(user_id, source);
            CREATE INDEX IF NOT EXISTS idx_sessions_token_hash 
                ON sessions(token_hash);
            CREATE INDEX IF NOT EXISTS idx_alerts_user_status
                ON user_alerts(user_id, status);
            CREATE INDEX IF NOT EXISTS idx_alerts_user_created
                ON user_alerts(user_id, created_at);
            """
        )
    conn.close()


# Initialize database upon import
init_db()
