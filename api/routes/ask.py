"""POST /ask — the main entry point. Routes to one of:

  • Orchestrator pipeline   — req.agent == "orchestrator"
  • Deep / Computer pipeline — req.mode in ("deep", "computer")
  • Quick pipeline           — single search → fetch → answer (or RAG-only when docs attached)

Streams Server-Sent Events. Persists user + assistant messages along the way.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agents.deep_research import run_deep_research
from agents.orchestrator import run_orchestrator
from agents.tools import build_messages
from auth import get_user_id
from config import HISTORY_TURNS, MODEL, RAG_TOP_K
from fetch import fetch_and_extract
from llm import llm
from rag import (
    doc_chunks_for_prompt,
    doc_chunks_to_sources,
    doc_belongs_to,
    retrieve_chunks,
)
from search import search_web
import threads_repo

router = APIRouter()


class AskRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None
    mode: str = "quick"                # "quick" | "deep" | "computer"
    focus: str = "web"                 # "web" | "academic" | "news" | "reddit"
    doc_ids: Optional[list[str]] = None
    agent: str = "generalist"          # "generalist" | "researcher" | "coder" | "analyst" | "orchestrator"


@router.post("/ask")
async def ask(req: AskRequest, user_id: str = Depends(get_user_id)):
    async def event_stream():
        thread_id = req.thread_id

        if thread_id:
            if not await threads_repo.thread_belongs_to(thread_id, user_id):
                yield {"event": "error", "data": "Thread not found."}
                yield {"event": "done", "data": ""}
                return
            history = await threads_repo.get_recent_messages(thread_id, HISTORY_TURNS * 2)
        else:
            thread_id = await threads_repo.create_thread(req.query, user_id=user_id)
            history = []

        yield {"event": "thread", "data": json.dumps({"id": thread_id, "mode": req.mode})}

        await threads_repo.insert_message(thread_id, "user", req.query)

        # Drop any doc_ids the user doesn't actually own.
        if req.doc_ids:
            owned = []
            for d in req.doc_ids:
                if await doc_belongs_to(d, user_id):
                    owned.append(d)
            req.doc_ids = owned or None

        # ---------- Orchestrator pipeline (multi-agent) ----------
        if req.agent == "orchestrator":
            collected_meta: list[dict] = []
            full_answer: list[str] = []
            async for evt in run_orchestrator(
                req.query, history, mode=req.mode, focus=req.focus, doc_ids=req.doc_ids,
            ):
                if evt["event"] == "sources":
                    try:
                        collected_meta = json.loads(evt["data"])
                    except Exception:
                        pass
                if evt["event"] == "token":
                    full_answer.append(evt["data"])
                yield evt

            answer_text = "".join(full_answer).strip()
            if answer_text:
                await threads_repo.insert_message(
                    thread_id, "assistant", answer_text, collected_meta or None,
                )
            await threads_repo.touch_thread(thread_id)
            yield {"event": "done", "data": ""}
            return

        # ---------- Deep / Computer pipeline (single agentic loop) ----------
        if req.mode in ("deep", "computer"):
            collected_meta = []
            full_answer = []
            async for evt in run_deep_research(
                req.query, history, mode=req.mode, focus=req.focus,
                doc_ids=req.doc_ids, agent=req.agent,
            ):
                if evt["event"] == "sources":
                    try:
                        collected_meta = json.loads(evt["data"])
                    except Exception:
                        pass
                if evt["event"] == "token":
                    full_answer.append(evt["data"])
                if evt["event"] == "final_answer":
                    continue  # internal signal, not for the client
                yield evt

            answer_text = "".join(full_answer).strip()
            if answer_text:
                await threads_repo.insert_message(
                    thread_id, "assistant", answer_text, collected_meta or None,
                )
            await threads_repo.touch_thread(thread_id)
            yield {"event": "done", "data": ""}
            return

        # ---------- Quick pipeline ----------

        # 1. RAG-only when documents are attached.
        if req.doc_ids:
            try:
                rows = await retrieve_chunks(req.doc_ids, req.query, top_k=RAG_TOP_K)
            except Exception as e:
                err_msg = f"RAG retrieval failed: {e}"
                await threads_repo.insert_message(thread_id, "assistant", err_msg)
                await threads_repo.touch_thread(thread_id)
                yield {"event": "error", "data": err_msg}
                yield {"event": "done", "data": ""}
                return

            meta = doc_chunks_to_sources(rows)
            yield {"event": "sources", "data": json.dumps(meta)}

            if not rows:
                msg = "No relevant passages found in the attached documents for this question."
                await threads_repo.insert_message(thread_id, "assistant", msg, meta)
                await threads_repo.touch_thread(thread_id)
                yield {"event": "token", "data": msg}
                yield {"event": "done", "data": ""}
                return

            sources = doc_chunks_for_prompt(rows)
            messages = build_messages(history, req.query, sources, agent=req.agent)
            full_answer: list[str] = []
            try:
                stream = await llm.chat.completions.create(
                    model=MODEL, messages=messages, temperature=0.3,
                    max_tokens=2048, stream=True,
                )
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta.content
                    if delta:
                        delta = delta.replace("【", "[").replace("】", "]")
                        full_answer.append(delta)
                        yield {"event": "token", "data": delta}
            except Exception as e:
                yield {"event": "error", "data": f"LLM error: {e}"}

            answer_text = "".join(full_answer).strip()
            if answer_text:
                await threads_repo.insert_message(thread_id, "assistant", answer_text, meta)
            await threads_repo.touch_thread(thread_id)
            yield {"event": "done", "data": ""}
            return

        # 2. Plain web search → fetch → answer.
        try:
            results = await search_web(req.query, focus=req.focus)
        except Exception as e:
            err_msg = f"Search failed: {e}"
            await threads_repo.insert_message(thread_id, "assistant", err_msg)
            await threads_repo.touch_thread(thread_id)
            yield {"event": "error", "data": err_msg}
            yield {"event": "done", "data": ""}
            return

        meta = [
            {"n": i + 1, "title": r["title"], "url": r["url"], "snippet": r["snippet"]}
            for i, r in enumerate(results)
        ]
        yield {"event": "sources", "data": json.dumps(meta)}

        texts = await fetch_and_extract([r["url"] for r in results])
        sources = [
            {"title": r["title"], "url": r["url"], "text": t}
            for r, t in zip(results, texts) if t
        ]

        if not sources:
            msg = "No readable sources were retrieved. Try rephrasing the question."
            await threads_repo.insert_message(thread_id, "assistant", msg, meta)
            await threads_repo.touch_thread(thread_id)
            yield {"event": "token", "data": msg}
            yield {"event": "done", "data": ""}
            return

        messages = build_messages(history, req.query, sources, agent=req.agent)
        full_answer: list[str] = []
        try:
            stream = await llm.chat.completions.create(
                model=MODEL, messages=messages, temperature=0.3,
                max_tokens=2048, stream=True,
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    delta = delta.replace("【", "[").replace("】", "]")
                    full_answer.append(delta)
                    yield {"event": "token", "data": delta}
        except Exception as e:
            yield {"event": "error", "data": f"LLM error: {e}"}

        answer_text = "".join(full_answer).strip()
        if answer_text:
            await threads_repo.insert_message(thread_id, "assistant", answer_text, meta)
        await threads_repo.touch_thread(thread_id)
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_stream())
