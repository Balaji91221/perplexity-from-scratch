# Lumen — How To Use It

A practical, scenario-driven guide. Each section is a real goal you might have, and the exact steps to reach it inside the app.

> **Goal of the project:** turn any question into a cited, streaming answer — using free, self-hosted infrastructure. Everything below builds on that core.

---

## 0 · Get the app running

Once.

```bash
# 1. Free NVIDIA key (no card needed)
echo 'NVIDIA_API_KEY=nvapi-...' > .env

# 2. Boot
docker compose up --build

# 3. Open the UI
open http://localhost:13000
```

Five containers come up: web, api, browser, searxng, postgres. If any one fails, see [README.md](README.md) for the service map.

---

## 1 · Get a quick cited answer

**Goal:** ask anything, get a clean answer with sources.

1. Open [localhost:13000](http://localhost:13000).
2. Type your question in the search box.
3. Press **Enter**.

What happens:

```
question  →  rewritten into 1-3 sub-queries  →  parallel SearXNG search
          →  fetch & extract top pages       →  build prompt with [N] sources
          →  stream LLM tokens to the UI     →  click [N] to open the source
```

**Tips**
- Multi-part questions like *"Compare React, Vue, and Svelte in 2026"* get auto-decomposed and search wider — you'll see the sub-queries chip strip above the source cards.
- Use the **focus tabs** in the header (Web / Academic / News / Reddit) to bias which engines SearXNG hits.

---

## 2 · Pick the right agent

**Goal:** match the answer style to the question type.

The agent dropdown (next to the search box) controls *how* the model answers, not *what* it knows:

| Agent | Use when |
|---|---|
| **Generalist** | Default. Balanced, conversational. |
| **Researcher** | You want section headers, balanced viewpoints, caveats. Great for "deep" mode. |
| **Coder** | You want a working code snippet first, prose second. |
| **Analyst** | You want tidy markdown tables. |
| **Orchestrator** | Question spans multiple skills — it dispatches sub-agents in parallel. |

---

## 3 · Use slash skills as one-tap shapers

**Goal:** force a specific output format without writing the instruction yourself.

Type `/` in the search box. The autocomplete pops with skills:

| Skill | Effect |
|---|---|
| `/tldr` | 3-bullet summary, no preamble. |
| `/explain` | Plain-language ELI5. |
| `/cite` | Adds an MLA Works Cited list. |
| `/code` | Working code block, run command underneath. |
| `/translate` | Translates the input (specify language in your message). |
| `/outline` | Hierarchical 3-level outline. |
| `/flashcards` | 8-card markdown table. |
| `/critique` | Strengths / Weaknesses / Risks. |
| `/extract` | Pulls structured fields into a markdown table. |

Example: type `/critique`, then *"my idea to launch a paid newsletter for indie game devs"*.

---

## 4 · Multi-step Deep Research

**Goal:** the model takes multiple steps and gives a denser answer.

1. Click the **mode** dropdown next to the search box.
2. Pick **Deep**.
3. Ask your question.

The agent now runs a tool-use loop: searches, reads, narrows, reads more, then synthesizes. You'll see a **Steps** section above the answer with each tool call (search → read_url → search → ...).

Cost: 5–10× more LLM calls than Quick mode. Use sparingly.

---

## 5 · Watch the agent browse (Computer Use)

**Goal:** see what the agent is reading, not just what it answers.

1. Mode → **Computer**.
2. Ask a question that needs primary-source pages.

For each page the agent visits, you'll get a screenshot in the Steps section. Same agent loop as Deep, just more visible.

---

## 6 · Autonomous site crawl (Assistant panel)

**Goal:** find a specific thing on a known site — pricing, deep doc page, comparison data — and have the agent click through pages to find it.

1. Click **Assistant** in the top-right.
2. **URL:** the site to start on, e.g. `https://stripe.com`.
3. **Goal:** what to find, e.g. `find pricing for the standard payments plan and any free-trial info`.
4. Leave **Stay on the same site** checked (default).
5. Click **Start**.

Live feed appears: each page card shows a screenshot, action chips for what the agent did, and finding cards as it extracts answers. A final synthesis streams at the bottom.

Defaults: 8 pages, 4 actions per page, 120s wall-clock budget. Stop anytime with the red Stop button.

**When to use:** the regular `/ask` flow can't reach the answer (paginated lists, JS-heavy pages, deep doc trees).
**When NOT to use:** simple factual questions — those are 1 LLM call vs. 30+ for a crawl.

---

## 7 · Ask questions about your own PDFs

**Goal:** drop a document in, ask anything about it.

1. Click the **paperclip** icon in the search box → upload a PDF (≤20 MB).
2. Wait for the toast: *"yourfile.pdf uploaded"*.
3. Ask your question.

The app retrieves the most relevant chunks via pgvector (no web search runs while a doc is attached). Every citation links to the exact page — click `[N]` and a right-side PDF viewer jumps there.

**Tips**
- Upload multiple PDFs to ask cross-document questions.
- Detach a doc by clicking the × on its chip in the search box.
- Stored PDFs stay in your sidebar's **Documents** section forever (per device) — re-attach with one click.

---

## 8 · Multi-turn conversations (threads)

**Goal:** keep context across follow-up questions.

- Every new question on the empty home page starts a thread.
- Once you're in a thread, the **bottom bar** lets you ask follow-ups — they include the last 3 turns as context.
- Threads auto-save to Postgres and group by date in the **left sidebar** (Today / Yesterday / Last 7 days / Earlier).
- Click any thread to reopen. Click **New thread** in the header to start fresh.
- Hover a thread → trash icon to delete (toast confirms).

---

## 9 · Plug in MCP tools

**Goal:** give the agent extra tools beyond search and read.

The app boots two MCP servers by default:
- **time** — get the current time, convert timezones.
- **fetch** — additional URL fetcher.

The sidebar's **MCP servers** section shows status (green dot = ok). Tool calls show up in the agent's Steps. To add more, edit `api/mcp_hub.py` and rebuild the API.

---

## 10 · Customize the brand

**Goal:** rename / re-skin the app.

Open [web/lib/constants.js](web/lib/constants.js) and edit the `BRAND` object:

```js
export const BRAND = {
  name: "YourName",
  tagline: "your tagline",
  hero: { title: ["First half", "second-half-with-gradient"], sub: "..." },
  features: ["Cited", "Multi-agent", "Streaming", "Open-source"],
};
```

Changes hot-reload. The favicon at [web/public/favicon.svg](web/public/favicon.svg) is brand-colored — swap if you want a different mark.

---

## Common pitfalls

| Symptom | Fix |
|---|---|
| Answers stream extremely slowly | NVIDIA free tier is overloaded — try a different time of day, or switch model in [api/config.py](api/config.py) (e.g. `meta/llama-3.1-70b-instruct`). |
| `/ask` returns empty source list | SearXNG service may be down — `docker compose ps` and check it's "Up". |
| Assistant panel "session not found" | Browser microservice restarted mid-run. Just click Start again. |
| PDF upload fails | File >20 MB, or it's image-only with no extractable text. |
| Agent picks wrong "Pricing" link | Crawler now uses indexed clickables — should be rare. If still happening, file an issue with the URL. |

---

## What success looks like

You should be able to, in under one minute each:

1. Ask *"What's new in Postgres 17?"* → get a 3-paragraph answer with 5 numbered citations linking to the official release notes, blog posts, etc.
2. Upload a 30-page PDF → ask *"Summarize the methodology section"* → get a citation that opens the PDF to the right page.
3. Open the Assistant panel with `https://anthropic.com` + `find the latest model and its context window` → watch it navigate, return a finding, and synthesize.

If those three flows work, you're at the project's goal — a self-hosted Perplexity that can answer, research deeply, and act.

---

## Where to extend next

- **/share/:id** public answer pages with OG images (growth feature).
- **Cmd+K** command palette (jump between threads / agents / docs).
- **Mobile responsive sweep** (sidebar drawer + stacked cards).
- **More MCP servers** (calendar, email, GitHub).
- **Fine-tune the local skills list** for your domain.

See [README.md](README.md) for architecture and [the assistant panel section](#6--autonomous-site-crawl-assistant-panel) above for the most ambitious feature.
