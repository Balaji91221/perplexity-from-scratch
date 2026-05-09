"""SearXNG search wrapper. The `focus` parameter selects category/engine."""

import asyncio

import httpx

from config import FOCUS_PARAMS, NUM_SOURCES, SEARXNG_URL


async def search_web(query: str, limit: int = NUM_SOURCES, focus: str = "web") -> list[dict]:
    extra = FOCUS_PARAMS.get(focus, FOCUS_PARAMS["web"])
    params = {"q": query, "format": "json", "safesearch": "1", **extra}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{SEARXNG_URL}/search", params=params)
        r.raise_for_status()
        data = r.json()

    seen = set()
    out: list[dict] = []
    for item in data.get("results", []):
        url = item.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(
            {"title": item.get("title", ""), "url": url, "snippet": item.get("content", "")}
        )
        if len(out) >= limit:
            break
    return out


async def multi_search(
    queries: list[str], limit: int = NUM_SOURCES, focus: str = "web"
) -> list[dict]:
    """Run several queries in parallel, interleave round-robin, dedupe by URL."""
    if not queries:
        return []
    if len(queries) == 1:
        return await search_web(queries[0], limit=limit, focus=focus)

    per_query = max(3, limit)
    results = await asyncio.gather(
        *(search_web(q, limit=per_query, focus=focus) for q in queries),
        return_exceptions=True,
    )
    lists = [r for r in results if isinstance(r, list)]
    if not lists:
        return []

    seen: set[str] = set()
    out: list[dict] = []
    for i in range(max(len(lst) for lst in lists)):
        for lst in lists:
            if i >= len(lst):
                continue
            item = lst[i]
            url = item.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            out.append(item)
            if len(out) >= limit:
                return out
    return out
