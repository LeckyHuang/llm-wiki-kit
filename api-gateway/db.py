"""
API Gateway 数据库层
管理：注册应用（App）、API 密钥（Key）、访问日志（Log）
使用 SQLite，与 wiki-app 的数据库完全独立。
"""
import sqlite3
from config import GW_DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(GW_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.executescript("""
        -- 注册的接入应用
        CREATE TABLE IF NOT EXISTS apps (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    UNIQUE NOT NULL,
            description  TEXT    DEFAULT '',
            contact      TEXT    DEFAULT '',
            scopes       TEXT    DEFAULT 'query,chat,wiki',
            rate_limit   INTEGER DEFAULT 60,
            is_active    INTEGER DEFAULT 1,
            created_at   TEXT    DEFAULT (datetime('now', 'localtime'))
        );

        -- API 密钥（存储 SHA-256 哈希，明文仅在创建时返回一次）
        CREATE TABLE IF NOT EXISTS api_keys (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            app_id       INTEGER NOT NULL REFERENCES apps(id) ON DELETE CASCADE,
            label        TEXT    NOT NULL DEFAULT 'default',
            key_hash     TEXT    UNIQUE NOT NULL,
            key_prefix   TEXT    NOT NULL,
            is_active    INTEGER DEFAULT 1,
            last_used_at TEXT,
            created_at   TEXT    DEFAULT (datetime('now', 'localtime'))
        );

        -- 访问日志
        CREATE TABLE IF NOT EXISTS gateway_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            app_id      INTEGER,
            key_id      INTEGER,
            app_name    TEXT,
            endpoint    TEXT,
            method      TEXT,
            status_code INTEGER,
            latency_ms  INTEGER,
            created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_gateway_logs_app_id  ON gateway_logs(app_id);
        CREATE INDEX IF NOT EXISTS idx_gateway_logs_created ON gateway_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_api_keys_hash        ON api_keys(key_hash);
    """)
    conn.commit()
    conn.close()
