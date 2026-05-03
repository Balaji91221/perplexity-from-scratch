"""SearXNG search wrapper. The `focus` parameter selects category/engine."""

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
