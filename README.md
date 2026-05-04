# Perplexity Clone — from scratch

Build a Perplexity-style answer engine, stage by stage. Free to run end-to-end.

```
question → SearXNG search → fetch & extract → prompt build → gpt-oss-120b → cited streaming answer
```

## Stack (locked)

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 (port 3000) | SSE streaming + React |
| Backend | FastAPI (port 8000) | Async + SSE trivial |
| Search | SearXNG (self-hosted, port 8080) | Free, no API key, multi-engine |
| LLM | NVIDIA NIM `gpt-oss-120b` | Free build credits |
| Page extract | `httpx` + `trafilatura` | Concurrent fetch + clean text |
| DB | Postgres + pgvector (port 5432) | Chat history now, embeddings later |
| Run | Docker Compose | One command boot |

## Quick start

1. Get a free NVIDIA API key at https://build.nvidia.com/ (no card required).
2. `cp .env.example .env` and paste your key.
3. `docker compose up`
4. Open http://localhost:3000 — should show "api: ok".

## Build phases

- [x] **Phase 0** — Scaffolding. Three services boot, web reaches api `/health`.
- [ ] **Phase 1** — The 5-stage pipeline (`/ask` endpoint, SSE streaming).
  1. `search_web(query, focus)` → list of `{title, url, snippet}` via SearXNG
  2. `fetch_and_extract(urls)` → list of `{url, text}` (parallel httpx + trafilatura)
  3. `build_prompt(query, sources)` → messages with numbered sources, citation rules
  4. `stream_llm(messages)` → async iterator of token deltas
  5. `POST /ask` → orchestrate 1→4, return `text/event-stream`
- [ ] **Phase 2** — Frontend streaming + clickable `[N]` citations + source cards.
- [ ] **Phase 3** — Postgres-backed thread history, multi-turn context, sidebar.
- [ ] **Phase 4** — Quality wins: query rewriting, Redis cache, chunking + pgvector, hybrid search, reranker.
- [ ] **Phase 5** — Focus modes (Academic, Reddit, YouTube), image results, PDF upload, auth.

## Project layout

```
perplexity-from-scratch/
├── docker-compose.yml          three services
├── .env.example                paste NVIDIA key here, copy to .env
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py                 Phase 0: /health only. Phase 1 adds /ask.
├── web/
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── pages/index.js          Phase 0: input form. Phase 2 wires SSE.
│   └── styles/globals.css
└── db/
    └── init.sql                pgvector extension; tables added in Phase 3.
```

## Phase 0 acceptance test

```bash
docker compose up
# In another shell:
curl http://localhost:8000/health        # -> {"status":"ok"}
open http://localhost:3000               # -> page shows "api: ok"
```

If both pass, you're ready for Phase 1.
