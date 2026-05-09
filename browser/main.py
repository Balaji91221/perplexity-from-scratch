"""FastAPI entry point for the headless browser microservice.

Endpoints:
  GET  /health                   service + browser status
  GET  /browse                   one-shot render+extract (legacy, no session)
  POST /session                  create a persistent browser session
  POST /action                   {session_id, kind, target?, value?} → snapshot
  DELETE /session/{session_id}   close a session
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

import browser_pool
from actions import do_action
from extract import render_and_extract


@asynccontextmanager
async def lifespan(app: FastAPI):
    await browser_pool.ensure_browser()
    yield
    await browser_pool.close()


app = FastAPI(title="Browser Service", lifespan=lifespan)


class ActionRequest(BaseModel):
    session_id: str
    kind: str
    target: str | None = None
    value: str | None = None


@app.get("/health")
async def health():
    return {"status": "ok", "browser_ready": browser_pool.is_ready()}


@app.get("/browse")
async def browse(url: str, max_chars: int = 4000, screenshot: bool = False):
    return await render_and_extract(url, max_chars=max_chars, screenshot=screenshot)


@app.post("/session")
async def open_session():
    sid = await browser_pool.create_session()
    return {"session_id": sid}


@app.post("/action")
async def action(req: ActionRequest):
    return await do_action(
        req.session_id,
        {"kind": req.kind, "target": req.target, "value": req.value},
    )


@app.delete("/session/{session_id}")
async def end_session(session_id: str):
    closed = await browser_pool.close_session(session_id)
    return {"closed": closed}
