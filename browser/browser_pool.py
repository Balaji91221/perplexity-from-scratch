"""Singleton Playwright Chromium browser. One process-wide instance, lazy start.

The actual page navigation happens in `extract.py`; this module just owns the
long-lived browser handle so we don't pay launch cost per request.
"""

from typing import Optional

from playwright.async_api import Browser, Playwright, async_playwright

_state: dict = {}


async def ensure_browser() -> Browser:
    if "browser" not in _state:
        pw: Playwright = await async_playwright().start()
        _state["pw"] = pw
        _state["browser"] = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
    return _state["browser"]


def is_ready() -> bool:
    return "browser" in _state


async def close() -> None:
    if "browser" in _state:
        await _state["browser"].close()
    if "pw" in _state:
        await _state["pw"].stop()
    _state.clear()
