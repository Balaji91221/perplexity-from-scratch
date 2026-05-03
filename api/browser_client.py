"""HTTP client for the headless `browser` microservice (Playwright).

Returns the rendered text plus, optionally, a base64 JPEG screenshot
(used by Computer Use mode).
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
