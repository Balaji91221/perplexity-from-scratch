"""FastAPI entry point. Wires the app together — everything else is in modules.

File map (back-end):
  config.py         — env vars + tunable constants
  db.py             — Postgres connection helper + schema migration
  auth.py           — get_user_id dependency (X-User-Id header / ?uid= fallback)
  llm.py            — AsyncOpenAI client + embed_texts
  search.py         — SearXNG search wrapper
  fetch.py          — httpx + trafilatura static fetch
  browser_client.py — HTTP client to the headless `browser` microservice
  pdf.py            — PDF parse + paragraph chunk
  rag.py            — pgvector storage + retrieval, source-shape helpers
  threads_repo.py   — threads + messages persistence
  mcp_hub.py        — MCP stdio servers (time, fetch) + tool dispatch
  agents/           — agentic layer
    prompts.py        all system prompts
    registry.py       AGENTS preset dict + resolve_agent
    tools.py          tool impls + schemas + per-call factory + build_messages
    deep_research.py  single-agent tool-call loop (Quick / Deep / Computer modes)
    orchestrator.py   multi-agent: planner → specialists → synthesizer
  routes/           — HTTP layer
    threads.py        /threads, /threads/{id}
    documents.py      /documents, /documents/upload, /documents/{id}/file
    agents.py         /agents
    mcp.py            /mcp/servers
    ask.py            /ask  (the main streaming endpoint)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from db import run_schema_migration
from mcp_hub import hub as mcp_hub
from routes import all_routers


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_schema_migration()
    # MCP servers are best-effort; failure to spawn one doesn't block startup.
    try:
        await mcp_hub.start()
    except Exception as e:
        logging.getLogger("uvicorn").warning("MCP hub failed to start: %s", e)
    yield
    await mcp_hub.close()


app = FastAPI(title="Perplexity Clone API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


for router in all_routers():
    app.include_router(router)
