"""LLM-driven query rewriting.

Decomposes a user question into 1-3 focused web-search queries. Falls back to
the original query on any error or when rewriting isn't worth it (very short
queries, simple lookups).
"""

import json
from typing import Optional

from config import MODEL
from llm import llm

REWRITE_PROMPT = """You are a search query planner. Given a user question (and recent chat context if any), output 1-3 short web-search queries that together would surface the best evidence to answer it.

Rules:
- Prefer keyword-style queries (no question marks, no filler words like "how to", "what is").
- If the question has multiple distinct sub-parts, decompose into separate queries — one per sub-part.
- If the question is a simple lookup, return just ONE query (the cleaned-up form).
- Never output more than 3 queries.
- Return ONLY a JSON array of strings. No prose, no markdown.

Examples:
Q: "What's the latest on the Artemis II mission?"
A: ["Artemis II mission status 2026", "Artemis II launch date"]

Q: "Compare Postgres and MySQL for analytics workloads"
A: ["Postgres analytics performance benchmark", "MySQL analytics performance benchmark", "Postgres vs MySQL OLAP"]

Q: "capital of france"
A: ["capital of France"]
"""


def _should_skip(query: str) -> bool:
    q = query.strip()
    if len(q) < 12:
        return True
    if len(q.split()) < 4:
        return True
    return False


async def rewrite_query(query: str, history: Optional[list[dict]] = None) -> list[str]:
    """Return 1-3 sub-queries. Always includes a usable fallback."""
    if _should_skip(query):
        return [query.strip()]

    messages = [{"role": "system", "content": REWRITE_PROMPT}]
    if history:
        recent = [m for m in history[-4:] if m.get("role") in ("user", "assistant")]
        if recent:
            ctx = "\n".join(f"{m['role']}: {m.get('content','')[:200]}" for m in recent)
            messages.append({"role": "system", "content": f"Recent context:\n{ctx}"})
    messages.append({"role": "user", "content": query})

    try:
        resp = await llm.chat.completions.create(
            model=MODEL, messages=messages, temperature=0.2, max_tokens=200,
        )
        raw = (resp.choices[0].message.content or "").strip()
        # Tolerate code-fenced JSON.
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        start, end = raw.find("["), raw.rfind("]")
        if start == -1 or end == -1:
            return [query.strip()]
        arr = json.loads(raw[start : end + 1])
        out: list[str] = []
        for s in arr:
            if isinstance(s, str):
                s = s.strip()
                if s and s.lower() not in (q.lower() for q in out):
                    out.append(s)
            if len(out) >= 3:
                break
        return out or [query.strip()]
    except Exception:
        return [query.strip()]
