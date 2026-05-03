"""Tool layer for the agentic loop.

- TOOLS_SCHEMA          — OpenAI-format tool schemas presented to the LLM
- tool_search / tool_read_url / tool_browse_url / tool_read_doc — implementations
- _make_tool_impls(...) — bind impls to per-call options (mode, focus, doc_ids)
- _tools_schema(...)    — final schema list, with optional read_doc + MCP tools, agent whitelist
"""

import json
from typing import Optional

from config import MAX_CHARS_PER_SOURCE, NUM_SOURCES, RAG_TOP_K
from search import search_web
from fetch import fetch_one_url
from browser_client import browse_url as browse_via_service
from rag import retrieve_chunks
from mcp_hub import hub as mcp_hub

from .registry import resolve_agent


# OpenAI-format tool schemas presented to the LLM.
TOOLS_SCHEMA: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search the web. Returns up to 6 results with title, URL, and snippet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The web search query."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_url",
            "description": "Fetch a URL with fast HTTP and extract its readable text. Best for static articles.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browse_url",
            "description": "Render a URL in a real headless browser. Use only when read_url returns empty/sparse text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to render."},
                },
                "required": ["url"],
            },
        },
    },
]


# ---------- Tool implementations ----------

async def tool_search(args: dict, focus: str = "web") -> tuple[str, dict]:
    query = args.get("query", "")
    try:
        results = await search_web(query, limit=NUM_SOURCES, focus=focus)
    except Exception as e:
        return f"search error: {e}", {"error": str(e)}
    lines = [f"Search results for: {query}"]
    for i, r in enumerate(results, start=1):
        lines.append(f"[{i}] {r['title']}\n    URL: {r['url']}\n    {r['snippet']}")
    return "\n".join(lines), {"query": query, "results": results}


async def tool_read_url(args: dict) -> tuple[str, dict]:
    url = args.get("url", "")
    try:
        text = await fetch_one_url(url)
    except Exception as e:
        return f"read_url error: {e}", {"url": url, "error": str(e)}
    if not text:
        return (
            f"read_url returned empty for {url}. The page may be JavaScript-heavy; try browse_url.",
            {"url": url, "ok": False},
        )
    return f"Content from {url}:\n\n{text}", {"url": url, "ok": True, "chars": len(text)}


async def tool_browse_url(args: dict, screenshot: bool = False) -> tuple[str, dict]:
    url = args.get("url", "")
    try:
        data = await browse_via_service(url, screenshot=screenshot)
    except Exception as e:
        return f"browse_url error: {e}", {"url": url, "error": str(e)}
    text = data.get("text", "")
    payload = {"url": url, "ok": bool(text), "chars": len(text), "title": data.get("title", "")}
    if data.get("screenshot"):
        payload["screenshot"] = data["screenshot"]
    if not text:
        return f"browse_url rendered {url} but extracted no readable text.", payload
    return f"Rendered content from {url}:\n\n{text}", payload


def _make_read_doc_tool(doc_ids: list[str]):
    async def read_doc(args: dict) -> tuple[str, dict]:
        q = args.get("query", "")
        try:
            rows = await retrieve_chunks(doc_ids, q, top_k=RAG_TOP_K)
        except Exception as e:
            return f"read_doc error: {e}", {"error": str(e)}
        if not rows:
            return f"No matching passages found in attached documents for: {q}", {"hits": 0}
        text = "Top matching passages from attached documents:\n\n" + "\n\n".join(
            f"[{i+1}] {r['filename']}, page {r['page']}:\n{r['content']}"
            for i, r in enumerate(rows)
        )
        ui = {
            "query": q,
            "hits": len(rows),
            # _rows is consumed by run_deep_research to track collected sources;
            # stripped before the SSE step_result is sent to the client.
            "_rows": rows,
            "results": [
                {"filename": r["filename"], "page": r["page"], "snippet": r["content"][:200]}
                for r in rows
            ],
        }
        return text, ui

    return read_doc


# ---------- Per-call binding ----------

def make_tool_impls(mode: str, focus: str = "web", doc_ids: Optional[list[str]] = None) -> dict:
    """Tool implementations bound to the current mode, focus, and optional attached docs."""
    take_screenshots = mode == "computer"
    doc_ids = doc_ids or []

    async def search_with_focus(args):
        return await tool_search(args, focus=focus)

    async def browse_with_mode(args):
        return await tool_browse_url(args, screenshot=take_screenshots)

    impls = {
        "search": search_with_focus,
        "read_url": tool_read_url,
        "browse_url": browse_with_mode,
    }
    if doc_ids:
        impls["read_doc"] = _make_read_doc_tool(doc_ids)
    return impls


def make_tools_schema(doc_ids: Optional[list[str]] = None, agent: Optional[str] = None) -> list[dict]:
    """Final tool schema list — built-ins + read_doc + MCP tools, optionally pruned by agent whitelist."""
    schema = list(TOOLS_SCHEMA)
    if doc_ids:
        schema.append({
            "type": "function",
            "function": {
                "name": "read_doc",
                "description": (
                    "Semantic search across the user's uploaded documents. "
                    "Returns up to 6 most relevant passages with their filename and page number. "
                    "Use this BEFORE web search when the question is about an uploaded document."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search phrase. Use natural language."},
                    },
                    "required": ["query"],
                },
            },
        })
    schema.extend(mcp_hub.list_tool_schemas())

    cfg = resolve_agent(agent)
    whitelist = cfg.get("tool_whitelist")
    if whitelist:
        allow_mcp = "mcp_*" in whitelist
        filtered = []
        for s in schema:
            name = s["function"]["name"]
            if name in whitelist:
                filtered.append(s)
            elif allow_mcp and name.startswith("mcp_"):
                filtered.append(s)
        return filtered
    return schema


# ---------- Common helpers used by deep_research and quick mode ----------

def build_messages(history: list[dict], query: str, sources: list[dict],
                   agent: Optional[str] = None) -> list[dict]:
    """Build the chat message list for quick mode (and as a fallback inside deep loops)."""
    from .prompts import SYSTEM_PROMPT  # local import to avoid cycles
    block = "\n\n".join(
        f"[{i+1}] {s['title']}\nURL: {s['url']}\n{s['text']}"
        for i, s in enumerate(sources)
    )
    cfg = resolve_agent(agent)
    sys_prompt = cfg.get("system_prompt") or SYSTEM_PROMPT
    return [
        {"role": "system", "content": sys_prompt},
        *history,
        {"role": "user", "content": f"Sources:\n\n{block}\n\nQuestion: {query}"},
    ]


def collected_to_meta(s: dict) -> dict:
    """Turn an internal collected-source dict into the SSE 'sources' payload shape."""
    base = {"n": s["n"], "title": s["title"], "url": s["url"], "snippet": s["text"][:280]}
    if s.get("type") == "doc":
        base["type"] = "doc"
        base["page"] = s.get("page")
        base["filename"] = s.get("filename")
        base["doc_id"] = s.get("doc_id")
    return base


def title_from_search_results(url: str, search_log: list[dict]) -> str:
    """Look back through prior search calls to find a title for this URL."""
    for entry in search_log:
        for r in entry.get("results", []):
            if r.get("url") == url:
                return r.get("title") or url
    return url
