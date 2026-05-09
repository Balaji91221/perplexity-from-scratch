"""Whitelisted browser actions executed against a persistent session.

Every action takes the same shape on the wire:
    {"kind": "...", "target": "...", "value": "..."}
and returns:
    {ok, url, title, text, screenshot, links, clickables, error?}

Hard rules:
  • No `evaluate` / raw JS injection.
  • No file downloads.
  • Only http(s) URLs.
  • Per-action 12s timeout.
"""

import base64
from typing import Any
from urllib.parse import urlparse

import trafilatura
from fastapi import HTTPException
from playwright.async_api import Page

import browser_pool

ACTION_TIMEOUT_MS = 12_000
MAX_TEXT_CHARS = 4000
MAX_CLICKABLES = 30
MAX_LINKS = 30


def _require_session(session_id: str) -> Page:
    s = browser_pool.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail=f"session {session_id} not found")
    return s["page"]


def _is_safe_url(url: str) -> bool:
    try:
        u = urlparse(url)
        return u.scheme in ("http", "https") and bool(u.netloc)
    except Exception:
        return False


async def _snapshot(page: Page, want_screenshot: bool = True) -> dict[str, Any]:
    """Capture the current state the agent will reason over."""
    try:
        title = await page.title()
    except Exception:
        title = ""
    url = page.url
    try:
        html = await page.content()
        text_full = trafilatura.extract(html) or ""
    except Exception:
        text_full = ""
    text = text_full[:MAX_TEXT_CHARS]

    clickables: list[dict] = []
    try:
        # Visible buttons + links + inputs with submit role.
        elements = await page.locator("a, button, [role=button], input[type=submit]").all()
        for i, el in enumerate(elements):
            if i >= MAX_CLICKABLES * 3:
                break
            try:
                if not await el.is_visible():
                    continue
                txt = (await el.inner_text())[:80].strip()
                href = await el.get_attribute("href")
                if not txt and not href:
                    continue
                clickables.append({"i": len(clickables), "text": txt, "href": href or ""})
                if len(clickables) >= MAX_CLICKABLES:
                    break
            except Exception:
                continue
    except Exception:
        pass

    links: list[dict] = []
    try:
        anchors = await page.locator("a[href]").all()
        for a in anchors[: MAX_LINKS * 3]:
            try:
                if not await a.is_visible():
                    continue
                href = await a.get_attribute("href")
                if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                    continue
                txt = (await a.inner_text())[:120].strip()
                links.append({"text": txt, "href": href})
                if len(links) >= MAX_LINKS:
                    break
            except Exception:
                continue
    except Exception:
        pass

    shot_b64 = None
    if want_screenshot:
        try:
            png = await page.screenshot(type="jpeg", quality=55, full_page=False)
            shot_b64 = "data:image/jpeg;base64," + base64.b64encode(png).decode("ascii")
        except Exception:
            shot_b64 = None

    return {
        "ok": True,
        "url": url,
        "title": title or "",
        "text": text,
        "screenshot": shot_b64,
        "links": links,
        "clickables": clickables,
    }


async def do_action(session_id: str, action: dict) -> dict:
    page = _require_session(session_id)
    kind = action.get("kind")
    target = action.get("target")
    value = action.get("value")

    try:
        if kind == "goto":
            if not target or not _is_safe_url(target):
                raise HTTPException(status_code=400, detail="goto requires a valid http(s) URL")
            await page.goto(target, wait_until="domcontentloaded", timeout=ACTION_TIMEOUT_MS)
            try:
                await page.wait_for_load_state("networkidle", timeout=4000)
            except Exception:
                pass

        elif kind == "click_text":
            if not target:
                raise HTTPException(status_code=400, detail="click_text requires target")
            loc = page.get_by_text(target, exact=False).first
            await loc.click(timeout=ACTION_TIMEOUT_MS)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=4000)
            except Exception:
                pass

        elif kind == "click_selector":
            if not target:
                raise HTTPException(status_code=400, detail="click_selector requires target")
            await page.locator(target).first.click(timeout=ACTION_TIMEOUT_MS)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=4000)
            except Exception:
                pass

        elif kind == "type":
            if not target:
                raise HTTPException(status_code=400, detail="type requires target selector")
            await page.locator(target).first.fill(value or "", timeout=ACTION_TIMEOUT_MS)

        elif kind == "press":
            if not value:
                raise HTTPException(status_code=400, detail="press requires value (key)")
            await page.keyboard.press(value)
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=4000)
            except Exception:
                pass

        elif kind == "scroll":
            direction = (target or "down").lower()
            amount = int(value) if (value and str(value).isdigit()) else 800
            dy = amount if direction == "down" else -amount
            await page.mouse.wheel(0, dy)

        elif kind in ("extract", "screenshot", "noop"):
            pass  # snapshot below covers it

        else:
            raise HTTPException(status_code=400, detail=f"unsupported action kind: {kind}")

    except HTTPException:
        raise
    except Exception as e:
        snap = await _snapshot(page, want_screenshot=True)
        snap["ok"] = False
        snap["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        return snap

    return await _snapshot(page, want_screenshot=True)
