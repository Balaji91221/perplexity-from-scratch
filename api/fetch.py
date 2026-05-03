"""Fast static HTTP fetch + readable-text extraction (httpx + trafilatura).

Used by the `read_url` tool and as the inline source pull in quick mode.
For JS-heavy sites, the agent falls back to the `browser` service via
`browser_client.browse_url`.
"""

import asyncio
from typing import Optional

import httpx
import trafilatura

from config import FETCH_TIMEOUT, MAX_CHARS_PER_SOURCE


async def _fetch_one(client: httpx.AsyncClient, url: str) -> Optional[str]:
    try:
        r = await client.get(
            url,
            follow_redirects=True,
            timeout=FETCH_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (perplexity-from-scratch)"},
        )
        if r.status_code != 200 or not r.text:
            return None
        text = trafilatura.extract(r.text) or ""
        return text[:MAX_CHARS_PER_SOURCE] if text else None
    except Exception:
        return None


async def fetch_and_extract(urls: list[str]) -> list[Optional[str]]:
    """Parallel fetch a list of URLs, return extracted text per URL (or None)."""
    async with httpx.AsyncClient() as client:
        return await asyncio.gather(*[_fetch_one(client, u) for u in urls])


async def fetch_one_url(url: str) -> Optional[str]:
    """Single-URL convenience wrapper for the read_url tool."""
    async with httpx.AsyncClient() as client:
        return await _fetch_one(client, url)
