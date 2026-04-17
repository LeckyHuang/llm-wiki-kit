import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "./data.db"))


def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(admin_password_hash: str) -> None:
    """建表并初始化管理员账号（admin / Lecky888）"""
    conn = get_db_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS su_names (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL UNIQUE,
            su_name       TEXT NOT NULL DEFAULT '',
            role          TEXT NOT NULL DEFAULT 'user',
            password_hash TEXT NOT NULL,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS usage_logs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER,
            user_name        TEXT,
            su_name          TEXT,
            function         TEXT NOT NULL,
            opportunity_name TEXT,
            query_params     TEXT,
            created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER,
            user_name    TEXT,
            usage_log_id INTEGER,
            rating       INTEGER NOT NULL,
            comment      TEXT,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS estimation_files (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            display_name TEXT NOT NULL,
            filename     TEXT NOT NULL UNIQUE,
            category     TEXT NOT NULL,
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # 若不存在则创建初始管理员
    row = conn.execute("SELECT id FROM users WHERE name = 'admin'").fetchone()
    if not row:
        conn.execute(
            "INSERT INTO users (name, su_name, role, password_hash) VALUES (?, ?, ?, ?)",
            ("admin", "", "admin", admin_password_hash),
        )
        conn.commit()

    conn.close()
