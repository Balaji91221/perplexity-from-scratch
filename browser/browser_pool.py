"""Singleton Playwright Chromium browser + interactive session map.

The single browser instance is reused across all requests. On top of that we
keep a `session_id → Page` map for interactive crawls where the agent needs
state (cookies, current URL, scroll position) to persist across actions.

Sessions auto-reap after IDLE_TTL_SEC of inactivity.
"""

import asyncio
import time
import uuid
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

IDLE_TTL_SEC = 300            # 5 min idle → reap
REAPER_INTERVAL_SEC = 30

_state: dict = {}
_sessions: dict[str, dict] = {}    # session_id -> {ctx, page, last_used}
_lock = asyncio.Lock()


async def ensure_browser() -> Browser:
    if "browser" not in _state:
        pw: Playwright = await async_playwright().start()
        _state["pw"] = pw
        _state["browser"] = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        _state["reaper"] = asyncio.create_task(_reap_idle_loop())
    return _state["browser"]


def is_ready() -> bool:
    return "browser" in _state


async def create_session() -> str:
    browser = await ensure_browser()
    ctx: BrowserContext = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        ),
    )
    page: Page = await ctx.new_page()
    sid = uuid.uuid4().hex
    _sessions[sid] = {"ctx": ctx, "page": page, "last_used": time.monotonic()}
    return sid


def get_session(session_id: str) -> Optional[dict]:
    s = _sessions.get(session_id)
    if s:
        s["last_used"] = time.monotonic()
    return s


async def close_session(session_id: str) -> bool:
    s = _sessions.pop(session_id, None)
    if not s:
        return False
    try:
        await s["ctx"].close()
    except Exception:
        pass
    return True


async def _reap_idle_loop() -> None:
    while True:
        try:
            await asyncio.sleep(REAPER_INTERVAL_SEC)
            cutoff = time.monotonic() - IDLE_TTL_SEC
            stale = [sid for sid, s in _sessions.items() if s["last_used"] < cutoff]
            for sid in stale:
                await close_session(sid)
        except asyncio.CancelledError:
            break
        except Exception:
            continue


async def close() -> None:
    for sid in list(_sessions.keys()):
        await close_session(sid)
    if "reaper" in _state:
        _state["reaper"].cancel()
    if "browser" in _state:
        await _state["browser"].close()
    if "pw" in _state:
        await _state["pw"].stop()
    _state.clear()
