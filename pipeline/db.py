import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area TEXT,
    conversation_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    sender TEXT NOT NULL,
    is_support INTEGER NOT NULL,
    is_media INTEGER NOT NULL DEFAULT 0,
    content TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    area TEXT,
    conversation_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    message_count INTEGER NOT NULL,
    first_response_seconds REAL,
    categoria TEXT,
    tema TEXT,
    sentimento TEXT,
    resumo TEXT,
    analyzed_at TEXT
);

-- Mensagens dos grupos por area (saude/educacao/assistencia). Sem sessao/
-- atendimento: aqui o objetivo e so classificar se a mensagem indica
-- reclamacao ou erro/problema na plataforma Piaui Primeira Infancia.
CREATE TABLE IF NOT EXISTS group_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    area TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    sender TEXT NOT NULL,
    is_media INTEGER NOT NULL DEFAULT 0,
    content TEXT NOT NULL,
    is_issue INTEGER,
    issue_categoria TEXT,
    issue_tema TEXT,
    issue_tipo TEXT,
    analyzed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_group_messages_area ON group_messages(area);
CREATE INDEX IF NOT EXISTS idx_group_messages_conversation ON group_messages(conversation_id);

-- Vetores TF-IDF das group_messages, usados para busca semantica local
-- (pipeline/search_messages.py), dedup por similaridade e pre-filtro
-- inteligente - tudo sem depender de nenhuma API externa.
CREATE TABLE IF NOT EXISTS message_embeddings (
    message_id INTEGER PRIMARY KEY,
    vector BLOB NOT NULL,
    model TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Rastreia quais arquivos .txt ja foram processados por pipeline/sync_data.py,
-- pra saber o que pular e o que tem conteudo novo numa proxima rodada.
CREATE TABLE IF NOT EXISTS ingested_files (
    path TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    area TEXT,
    conversation_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    message_count INTEGER NOT NULL,
    last_synced_at TEXT NOT NULL
);
"""


@contextmanager
def get_conn():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _ensure_column(conn, table, column, coltype):
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _ensure_column(conn, "group_messages", "issue_tipo", "TEXT")
        _ensure_column(conn, "messages", "area", "TEXT")
        _ensure_column(conn, "sessions", "area", "TEXT")
        _ensure_column(conn, "messages", "is_issue", "INTEGER")
        _ensure_column(conn, "messages", "issue_categoria", "TEXT")
        _ensure_column(conn, "messages", "issue_tema", "TEXT")
        _ensure_column(conn, "messages", "issue_tipo", "TEXT")
        _ensure_column(conn, "messages", "analyzed_at", "TEXT")
        conn.commit()
