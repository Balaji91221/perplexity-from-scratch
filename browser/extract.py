"""Render a URL in real Chromium, extract readable text, optionally screenshot."""

import asyncio
import base64

import trafilatura
from fastapi import HTTPException

import browser_pool

# Serialize so memory stays bounded. One page at a time is plenty for this use case.
_lock = asyncio.Lock()


async def render_and_extract(url: str, max_chars: int = 4000, screenshot: bool = False) -> dict:
    """Returns {url, title, text, ok, screenshot}. Raises HTTPException on render failure."""
    browser = await browser_pool.ensure_browser()
    async with _lock:
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
            ),
        )
        page = await ctx.new_page()
        shot_b64 = None
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            try:
                await page.wait_for_load_state("networkidle", timeout=8000)
            except Exception:
                pass  # best-effort
            html = await page.content()
            title = await page.title()
            if screenshot:
                # Viewport-only JPEG, moderate quality. Keeps payload <200 KB typically.
                png = await page.screenshot(type="jpeg", quality=55, full_page=False)
                shot_b64 = "data:image/jpeg;base64," + base64.b64encode(png).decode("ascii")
        except Exception as e:
            await ctx.close()
            raise HTTPException(status_code=502, detail=f"browse failed: {e}")
        await ctx.close()

    text = trafilatura.extract(html) or ""
    return {
        "url": url,
        "title": title or "",
        "text": text[:max_chars],
        "ok": bool(text),
        "screenshot": shot_b64,
    }
