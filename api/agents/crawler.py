"""Goal-driven autonomous crawler.

Orchestrates two LLM loops against a persistent browser session:
  inner — what action to take on the current page
  outer — which link to visit next

Streams SSE events for the right-side Assistant panel:
  crawl_start, crawl_page, crawl_action, crawl_action_result,
  crawl_finding, crawl_link_plan, crawl_summary, crawl_synthesis (token stream),
  crawl_done, error.

Inspired by browser-use's "indexed clickables" idea: the model picks an action
target by a stable integer index ([3], [7]) instead of inventing a CSS
selector. We translate the index back to a real selector before executing.
"""

import asyncio
import json
from typing import AsyncIterator
from urllib.parse import urljoin, urlparse

from browser_client import close_session, create_session, do_action
from config import MODEL
from llm import llm

from .prompts.crawler import (
    ACTION_PLANNER_PROMPT,
    EXTRACT_PROMPT,
    LINK_PLANNER_PROMPT,
)

DEFAULT_MAX_PAGES = 8
DEFAULT_MAX_ACTIONS_PER_PAGE = 4
DEFAULT_MAX_SECONDS = 120


def _strip_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:].strip()
    return s


def _parse_json_object(raw: str) -> dict | None:
    raw = _strip_fence(raw)
    a, b = raw.find("{"), raw.rfind("}")
    if a == -1 or b == -1 or b <= a:
        return None
    try:
        return json.loads(raw[a : b + 1])
    except Exception:
        return None


def _parse_json_array(raw: str) -> list | None:
    raw = _strip_fence(raw)
    a, b = raw.find("["), raw.rfind("]")
    if a == -1 or b == -1 or b <= a:
        return None
    try:
        return json.loads(raw[a : b + 1])
    except Exception:
        return None


def _registrable_domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        parts = host.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        return host
    except Exception:
        return ""


def _absolutize(href: str, base: str) -> str | None:
    if not href:
        return None
    if href.startswith(("javascript:", "mailto:", "tel:", "#")):
        return None
    try:
        return urljoin(base, href)
    except Exception:
        return None


def _format_page_for_action_planner(snap: dict, goal: str, history_actions: list[dict]) -> str:
    """Present the page as an indexed list of clickables — the model picks
    a target by index ([0], [1], ...) and we translate it to a real action."""
    clickables = snap.get("clickables") or []
    lines = [f"GOAL: {goal}", f"URL: {snap.get('url','')}", f"TITLE: {snap.get('title','')}"]
    text = (snap.get("text") or "")[:1500]
    if text:
        lines.append(f"PAGE TEXT (truncated):\n{text}")
    if clickables:
        lines.append(
            "CLICKABLES (use these indices for click_index):"
        )
        for c in clickables[:25]:
            i = c.get("i", "?")
            t = (c.get("text") or "").replace("\n", " ").strip()[:60] or "(no text)"
            href = (c.get("href") or "")[:80]
            tail = f"  → {href}" if href else ""
            lines.append(f"  [{i}] {t!r}{tail}")
    if history_actions:
        lines.append("ACTIONS YOU ALREADY TOOK ON THIS PAGE:")
        for a in history_actions[-4:]:
            lines.append(f"  - {a.get('kind')}({a.get('target') or ''})  → {a.get('result','?')}")
    return "\n".join(lines)


async def _plan_action(goal: str, snap: dict, history_actions: list[dict]) -> dict:
    user_msg = _format_page_for_action_planner(snap, goal, history_actions)
    resp = await llm.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": ACTION_PLANNER_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,
        max_tokens=200,
    )
    raw = resp.choices[0].message.content or ""
    obj = _parse_json_object(raw) or {"kind": "done", "rationale": "parser failure"}
    valid = {
        "goto", "click_text", "click_selector", "click_index",
        "type", "press", "scroll", "extract", "done",
    }
    if obj.get("kind") not in valid:
        obj = {"kind": "done", "rationale": f"unknown kind: {obj.get('kind')}"}
    return obj


async def _plan_links(goal: str, links: list[dict], visited: set[str], base_url: str) -> list[str]:
    if not links:
        return []
    lines = [f"GOAL: {goal}", f"VISITED ({len(visited)}):"]
    for v in list(visited)[-8:]:
        lines.append(f"  - {v}")
    lines.append("LINKS ON CURRENT PAGE:")
    for ln in links[:25]:
        t = (ln.get("text") or "").replace("\n", " ").strip()[:80]
        href = ln.get("href") or ""
        lines.append(f"  - {t!r}  {href}")
    resp = await llm.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": LINK_PLANNER_PROMPT},
            {"role": "user", "content": "\n".join(lines)},
        ],
        temperature=0.2,
        max_tokens=200,
    )
    raw = resp.choices[0].message.content or ""
    arr = _parse_json_array(raw) or []
    out: list[str] = []
    for u in arr:
        if not isinstance(u, str):
            continue
        absu = _absolutize(u, base_url) or u
        if absu and absu not in visited and absu not in out:
            out.append(absu)
        if len(out) >= 3:
            break
    return out


async def _extract_finding(goal: str, snap: dict) -> dict | None:
    text = (snap.get("text") or "")[:2200]
    if not text:
        return None
    prompt = EXTRACT_PROMPT.format(
        goal=goal, url=snap.get("url", ""), title=snap.get("title", ""), text=text
    )
    resp = await llm.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": prompt}],
        temperature=0.1,
        max_tokens=400,
    )
    raw = resp.choices[0].message.content or ""
    obj = _parse_json_object(raw)
    if not obj:
        return None
    fields = obj.get("fields") or {}
    summary = (obj.get("summary") or "").strip()
    conf = obj.get("confidence")
    try:
        conf = float(conf)
    except Exception:
        conf = 0.0
    if not fields and not summary:
        return None
    return {"fields": fields, "summary": summary, "confidence": max(0.0, min(1.0, conf))}


async def _synthesize(goal: str, findings: list[dict]) -> AsyncIterator[str]:
    if not findings:
        yield "I couldn't find an answer for the goal on the pages I visited."
        return
    bullets = []
    for f in findings:
        bullets.append(
            f"- {f['url']} — {f.get('summary','')} "
            f"(fields: {json.dumps(f.get('fields', {}), ensure_ascii=False)})"
        )
    user = (
        f"GOAL: {goal}\n\nFINDINGS FROM CRAWL:\n" + "\n".join(bullets) +
        "\n\nWrite a concise, well-structured final answer to the goal grounded in these findings. "
        "Cite source URLs inline as plain links. Use markdown."
    )
    stream = await llm.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a careful research synthesizer."},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
        max_tokens=900,
        stream=True,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def _resolve_index_target(action: dict, clickables: list[dict]) -> dict:
    """If the model returned `click_index`, translate it to a `click_text`
    against the indexed clickable so the existing actions endpoint can run it.
    """
    if action.get("kind") != "click_index":
        return action
    try:
        idx = int(action.get("target") if action.get("target") is not None else action.get("value"))
    except Exception:
        return {"kind": "done", "rationale": "click_index requires integer target"}
    for c in clickables:
        if c.get("i") == idx:
            text = (c.get("text") or "").strip()
            href = c.get("href") or ""
            if text:
                return {"kind": "click_text", "target": text[:80], "rationale": action.get("rationale", "")}
            if href:
                return {"kind": "goto", "target": href, "rationale": action.get("rationale", "")}
            break
    return {"kind": "done", "rationale": f"index {idx} not found in clickables"}


async def run_crawler(
    start_url: str,
    goal: str,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_actions_per_page: int = DEFAULT_MAX_ACTIONS_PER_PAGE,
    same_domain: bool = True,
) -> AsyncIterator[dict]:
    """Yield SSE-shaped dicts: {event, data}."""
    yield {"event": "crawl_start", "data": json.dumps({"goal": goal, "start_url": start_url})}

    if not start_url.startswith(("http://", "https://")):
        start_url = "https://" + start_url
    base_domain = _registrable_domain(start_url)

    try:
        session_id = await create_session()
    except Exception as e:
        yield {"event": "error", "data": f"failed to open browser session: {e}"}
        yield {"event": "crawl_done", "data": ""}
        return

    visited: set[str] = set()
    frontier: list[str] = [start_url]
    findings: list[dict] = []
    deadline = asyncio.get_event_loop().time() + DEFAULT_MAX_SECONDS

    try:
        while frontier and len(visited) < max_pages:
            if asyncio.get_event_loop().time() > deadline:
                yield {"event": "crawl_action_result", "data": json.dumps({"ok": False, "error": "time budget exhausted"})}
                break
            url = frontier.pop(0)
            if url in visited:
                continue
            if same_domain and base_domain and _registrable_domain(url) != base_domain:
                continue
            visited.add(url)

            try:
                snap = await do_action(session_id, "goto", target=url)
            except Exception as e:
                yield {"event": "crawl_action_result", "data": json.dumps({"ok": False, "error": str(e)[:200], "url": url})}
                continue

            yield {
                "event": "crawl_page",
                "data": json.dumps({
                    "url": snap.get("url", url),
                    "title": snap.get("title", ""),
                    "screenshot": snap.get("screenshot"),
                    "visited_count": len(visited),
                }),
            }

            page_actions: list[dict] = []
            extracted_here = False
            for step in range(max_actions_per_page):
                if asyncio.get_event_loop().time() > deadline:
                    break
                action = await _plan_action(goal, snap, page_actions)
                # Translate `click_index` → concrete action using the indexed clickables.
                action = _resolve_index_target(action, snap.get("clickables") or [])
                kind = action.get("kind")
                yield {
                    "event": "crawl_action",
                    "data": json.dumps({
                        "step": step + 1, "kind": kind,
                        "target": action.get("target"),
                        "value": action.get("value"),
                        "rationale": action.get("rationale", ""),
                    }),
                }
                if kind == "done":
                    page_actions.append({"kind": "done", "result": "ok"})
                    break
                if kind == "extract":
                    finding = await _extract_finding(goal, snap)
                    page_actions.append({"kind": "extract", "result": "ok" if finding else "empty"})
                    if finding:
                        finding["url"] = snap.get("url", url)
                        finding["title"] = snap.get("title", "")
                        findings.append(finding)
                        yield {"event": "crawl_finding", "data": json.dumps(finding)}
                        extracted_here = True
                    continue

                try:
                    snap = await do_action(
                        session_id,
                        kind,
                        target=action.get("target"),
                        value=str(action.get("value")) if action.get("value") is not None else None,
                    )
                except Exception as e:
                    page_actions.append({"kind": kind, "result": f"error: {e}"})
                    yield {"event": "crawl_action_result", "data": json.dumps({"ok": False, "error": str(e)[:200]})}
                    break

                page_actions.append({"kind": kind, "result": "ok" if snap.get("ok") else "fail"})
                yield {
                    "event": "crawl_action_result",
                    "data": json.dumps({
                        "ok": bool(snap.get("ok")),
                        "url": snap.get("url"),
                        "title": snap.get("title"),
                        "screenshot": snap.get("screenshot"),
                        "error": snap.get("error"),
                    }),
                }

            if not extracted_here:
                finding = await _extract_finding(goal, snap)
                if finding and (finding.get("summary") or finding.get("fields")):
                    finding["url"] = snap.get("url", url)
                    finding["title"] = snap.get("title", "")
                    findings.append(finding)
                    yield {"event": "crawl_finding", "data": json.dumps(finding)}

            current_url = snap.get("url", url)
            raw_links = snap.get("links") or []
            absolute_links = []
            for ln in raw_links:
                absu = _absolutize(ln.get("href", ""), current_url)
                if absu:
                    absolute_links.append({"text": ln.get("text", ""), "href": absu})
            next_urls = await _plan_links(goal, absolute_links, visited, current_url)
            if same_domain and base_domain:
                next_urls = [u for u in next_urls if _registrable_domain(u) == base_domain]
            for u in next_urls:
                if u not in visited and u not in frontier:
                    frontier.append(u)
            yield {"event": "crawl_link_plan", "data": json.dumps({"next": next_urls})}

        yield {
            "event": "crawl_summary",
            "data": json.dumps({"pages_visited": len(visited), "findings_count": len(findings)}),
        }

        async for delta in _synthesize(goal, findings):
            yield {"event": "crawl_synthesis", "data": delta}

    finally:
        await close_session(session_id)
        yield {"event": "crawl_done", "data": ""}
