"""Threads + messages persistence."""

import json
from typing import Optional

from db import db


async def create_thread(title: str, user_id: str) -> str:
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO threads (title, user_id) VALUES (%s, %s) RETURNING id",
                (title[:120], user_id),
            )
            row = await cur.fetchone()
            return str(row[0])


async def thread_belongs_to(thread_id: str, user_id: str) -> bool:
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM threads WHERE id = %s AND user_id = %s",
                (thread_id, user_id),
            )
            return (await cur.fetchone()) is not None


async def touch_thread(thread_id: str) -> None:
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE threads SET updated_at = NOW() WHERE id = %s",
                (thread_id,),
            )


async def insert_message(
    thread_id: str,
    role: str,
    content: str,
    sources: Optional[list] = None,
) -> None:
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO messages (thread_id, role, content, sources) VALUES (%s, %s, %s, %s)",
                (thread_id, role, content, json.dumps(sources) if sources else None),
            )


async def get_recent_messages(thread_id: str, limit: int) -> list[dict]:
    """Return the most recent (limit) messages for a thread, in chronological order."""
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT role, content FROM messages WHERE thread_id = %s "
                "ORDER BY created_at DESC LIMIT %s",
                (thread_id, limit),
            )
            rows = await cur.fetchall()
    rows.reverse()
    return [{"role": r[0], "content": r[1]} for r in rows]


async def list_threads(user_id: str) -> list[dict]:
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, title, created_at, updated_at FROM threads "
                "WHERE user_id = %s ORDER BY updated_at DESC LIMIT 200",
                (user_id,),
            )
            rows = await cur.fetchall()
    return [
        {
            "id": str(r[0]),
            "title": r[1],
            "created_at": r[2].isoformat(),
            "updated_at": r[3].isoformat(),
        }
        for r in rows
    ]


async def get_thread_with_messages(thread_id: str, user_id: str) -> Optional[dict]:
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, title, created_at FROM threads WHERE id = %s AND user_id = %s",
                (thread_id, user_id),
            )
            t = await cur.fetchone()
            if not t:
                return None
            await cur.execute(
                "SELECT role, content, sources, created_at FROM messages "
                "WHERE thread_id = %s ORDER BY created_at",
                (thread_id,),
            )
            msgs = await cur.fetchall()
    return {
        "id": str(t[0]),
        "title": t[1],
        "created_at": t[2].isoformat(),
        "messages": [
            {
                "role": m[0],
                "content": m[1],
                "sources": m[2],
                "created_at": m[3].isoformat(),
            }
            for m in msgs
        ],
    }


async def delete_thread(thread_id: str, user_id: str) -> None:
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM threads WHERE id = %s AND user_id = %s",
                (thread_id, user_id),
            )
