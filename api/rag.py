"""Document persistence + semantic retrieval over chunks via pgvector."""

from typing import Optional

from config import MAX_CHARS_PER_SOURCE, RAG_TOP_K
from db import db
from llm import embed_texts


def _vec_literal(values: list[float]) -> str:
    """Format a Python list of floats as a pgvector literal: '[1.0,2.0,...]'"""
    return "[" + ",".join(f"{v:.6f}" for v in values) + "]"


# ---------- Documents CRUD ----------

async def store_document(
    filename: str,
    pages: list[tuple[int, str]],
    chunks: list[dict],
    embeddings: list[list[float]],
    pdf_data: bytes,
    user_id: str,
) -> dict:
    char_count = sum(len(t) for _, t in pages)
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO documents (filename, pages, char_count, pdf_data, mime_type, user_id) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id, created_at",
                (filename, len(pages), char_count, pdf_data, "application/pdf", user_id),
            )
            row = await cur.fetchone()
            doc_id, created_at = str(row[0]), row[1]
            for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                await cur.execute(
                    "INSERT INTO chunks (document_id, chunk_index, page, content, embedding) "
                    "VALUES (%s, %s, %s, %s, %s::vector)",
                    (doc_id, i, chunk["page"], chunk["content"], _vec_literal(emb)),
                )
    return {
        "id": doc_id,
        "filename": filename,
        "pages": len(pages),
        "chunks": len(chunks),
        "char_count": char_count,
        "created_at": created_at.isoformat(),
    }


async def list_documents(user_id: str) -> list[dict]:
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT d.id, d.filename, d.pages, d.char_count, d.created_at, COUNT(c.id) AS n_chunks "
                "FROM documents d LEFT JOIN chunks c ON c.document_id = d.id "
                "WHERE d.user_id = %s "
                "GROUP BY d.id ORDER BY d.created_at DESC LIMIT 200",
                (user_id,),
            )
            rows = await cur.fetchall()
    return [
        {
            "id": str(r[0]),
            "filename": r[1],
            "pages": r[2],
            "char_count": r[3],
            "created_at": r[4].isoformat(),
            "chunks": r[5],
        }
        for r in rows
    ]


async def doc_belongs_to(doc_id: str, user_id: str) -> bool:
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT 1 FROM documents WHERE id = %s AND user_id = %s",
                (doc_id, user_id),
            )
            return (await cur.fetchone()) is not None


async def get_document_file(doc_id: str, user_id: str) -> Optional[tuple[bytes, str, str]]:
    """Return (pdf_bytes, filename, mime_type) or None if not owned/found."""
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT pdf_data, filename, mime_type FROM documents "
                "WHERE id = %s AND user_id = %s",
                (doc_id, user_id),
            )
            row = await cur.fetchone()
    if not row or not row[0]:
        return None
    return bytes(row[0]), row[1], row[2] or "application/pdf"


async def delete_document(doc_id: str, user_id: str) -> None:
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "DELETE FROM documents WHERE id = %s AND user_id = %s",
                (doc_id, user_id),
            )


# ---------- Retrieval ----------

async def retrieve_chunks(doc_ids: list[str], query: str, top_k: int = RAG_TOP_K) -> list[dict]:
    """Cosine-similarity retrieval across the given documents."""
    if not doc_ids:
        return []
    qe = (await embed_texts([query], input_type="query"))[0]
    qe_lit = _vec_literal(qe)
    placeholders = ",".join(["%s"] * len(doc_ids))
    sql = (
        f"SELECT c.id, c.document_id, c.chunk_index, c.page, c.content, "
        f"       d.filename, "
        f"       1 - (c.embedding <=> %s::vector) AS similarity "
        f"FROM chunks c "
        f"JOIN documents d ON d.id = c.document_id "
        f"WHERE c.document_id IN ({placeholders}) "
        f"ORDER BY c.embedding <=> %s::vector "
        f"LIMIT %s"
    )
    params = [qe_lit, *doc_ids, qe_lit, top_k]
    async with db() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
    return [
        {
            "chunk_id": str(r[0]),
            "document_id": str(r[1]),
            "chunk_index": r[2],
            "page": r[3],
            "content": r[4],
            "filename": r[5],
            "similarity": float(r[6]),
        }
        for r in rows
    ]


# ---------- Conversion helpers (chunks → "source"-shaped objects) ----------

def doc_chunks_to_sources(rows: list[dict]) -> list[dict]:
    """Convert retrieved chunks into the same shape used for web sources (frontend SSE)."""
    return [
        {
            "n": i + 1,
            "type": "doc",
            "title": f"{r['filename']} — Page {r['page']}" if r.get("page") else r["filename"],
            "url": f"#document/{r['document_id']}#chunk-{r['chunk_index']}",
            "doc_id": r["document_id"],
            "page": r.get("page"),
            "filename": r["filename"],
            "snippet": (r["content"][:280] + "…") if len(r["content"]) > 280 else r["content"],
        }
        for i, r in enumerate(rows)
    ]


def doc_chunks_for_prompt(rows: list[dict]) -> list[dict]:
    """Shape chunks like web sources for build_messages()."""
    return [
        {
            "title": f"{r['filename']} — Page {r['page']}" if r.get("page") else r["filename"],
            "url": f"document://{r['document_id']}#chunk-{r['chunk_index']}",
            "text": r["content"],
        }
        for r in rows
    ]


# ---------- Truncation cap (re-export for tools) ----------

__all__ = [
    "store_document", "list_documents", "doc_belongs_to", "get_document_file",
    "delete_document", "retrieve_chunks", "doc_chunks_to_sources", "doc_chunks_for_prompt",
    "MAX_CHARS_PER_SOURCE",
]
