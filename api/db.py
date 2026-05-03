"""Postgres connection helper + idempotent schema migration."""

from contextlib import asynccontextmanager

import psycopg

from config import ANON_USER_ID, DATABASE_URL

SCHEMA_SQL = f"""
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    sources JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    pages INT NOT NULL,
    char_count INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    page INT,
    content TEXT NOT NULL,
    embedding vector(1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE threads   ADD COLUMN IF NOT EXISTS user_id UUID NOT NULL DEFAULT '{ANON_USER_ID}';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS user_id UUID NOT NULL DEFAULT '{ANON_USER_ID}';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS pdf_data BYTEA;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS mime_type TEXT;

CREATE INDEX IF NOT EXISTS idx_messages_thread   ON messages(thread_id, created_at);
CREATE INDEX IF NOT EXISTS idx_threads_user      ON threads(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_threads_updated   ON threads(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chunks_doc        ON chunks(document_id, chunk_index);
CREATE INDEX IF NOT EXISTS idx_documents_user    ON documents(user_id, created_at DESC);
"""


@asynccontextmanager
async def db():
    """One-shot async DB connection. Use as `async with db() as conn:`."""
    conn = await psycopg.AsyncConnection.connect(DATABASE_URL, autocommit=True)
    try:
        yield conn
    finally:
        await conn.close()


async def run_schema_migration() -> None:
    """Apply idempotent schema migrations at startup."""
    async with await psycopg.AsyncConnection.connect(DATABASE_URL, autocommit=True) as conn:
        async with conn.cursor() as cur:
            await cur.execute(SCHEMA_SQL)
