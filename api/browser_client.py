"""HTTP client for the headless `browser` microservice (Playwright).

Two surfaces:
  • browse_url(url) — one-shot render + extract (used by Computer Use mode).
  • create_session / do_action / close_session — interactive sessions for the
    autonomous crawler (right-side Assistant panel).
"""

import httpx

from config import BROWSER_URL


async def browse_url(url: str, screenshot: bool = False) -> dict:
    """Render `url` in real Chromium via the browser service. Raises on transport errors."""
    params: dict = {"url": url}
    if screenshot:
        params["screenshot"] = "true"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(f"{BROWSER_URL}/browse", params=params)
    r.raise_for_status()
    return r.json()


async def create_session() -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{BROWSER_URL}/session")
    r.raise_for_status()
    return r.json()["session_id"]


async def do_action(session_id: str, kind: str, target: str | None = None, value: str | None = None) -> dict:
    payload = {"session_id": session_id, "kind": kind, "target": target, "value": value}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{BROWSER_URL}/action", json=payload)
    r.raise_for_status()
    return r.json()


async def close_session(session_id: str) -> bool:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            r = await client.delete(f"{BROWSER_URL}/session/{session_id}")
            return r.status_code == 200
        except Exception:
            return False
