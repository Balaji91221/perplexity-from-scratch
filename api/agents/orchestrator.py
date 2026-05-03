"""Multi-agent orchestrator: planner → specialists → synthesizer.

Public surface: `run_orchestrator(...)` — async generator yielding SSE events.

Streamed event types in addition to those from `run_deep_research`:
  agent_phase     — { phase: "planning" | "running" | "synthesizing" | "done", index?, agent?, subtask? }
  plan            — { plan: [ { agent, subtask } ] }
  sub_step        — sub-agent's step event (sub_index attached)
  sub_step_result — sub-agent's step_result event
  sub_error       — sub-agent crashed
"""

import json
import re
from typing import Optional

from config import MODEL
from llm import llm

from .deep_research import run_deep_research
from .prompts import ORCHESTRATOR_PLANNER_PROMPT, ORCHESTRATOR_SYNTH_PROMPT
from .registry import AGENTS


async def _llm_call_for_plan(query: str) -> list[dict]:
    """Single non-streaming LLM call to produce the orchestrator plan."""
    try:
        resp = await llm.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": ORCHESTRATOR_PLANNER_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0.1,
            max_tokens=400,
            response_format={"type": "json_object"},
        )
        raw = (resp.choices[0].message.content or "").strip()
    except Exception:
        # Endpoint may not support response_format; retry without it.
        resp = await llm.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": ORCHESTRATOR_PLANNER_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0.1,
            max_tokens=400,
        )
        raw = (resp.choices[0].message.content or "").strip()

    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.S)
    try:
        data = json.loads(raw)
    except Exception:
        return []

    plan = data.get("plan") if isinstance(data, dict) else None
    if not isinstance(plan, list):
        return []

    cleaned: list[dict] = []
    for step in plan[:3]:
        if not isinstance(step, dict):
            continue
        agent = step.get("agent")
        sub = step.get("subtask")
        if agent in ("researcher", "coder", "analyst") and isinstance(sub, str) and sub.strip():
            cleaned.append({"agent": agent, "subtask": sub.strip()})
    return cleaned


async def run_orchestrator(
    query: str,
    history: list[dict],
    mode: str = "deep",
    focus: str = "web",
    doc_ids: Optional[list[str]] = None,
):
    """Async generator. Decomposes the query, runs each specialist, then synthesizes."""
    doc_ids = doc_ids or []

    yield {"event": "agent_phase", "data": json.dumps({"phase": "planning"})}

    plan = await _llm_call_for_plan(query)
    if not plan:
        plan = [{"agent": "researcher", "subtask": query}]

    yield {"event": "plan", "data": json.dumps({"plan": plan})}

    sub_results: list[dict] = []
    unified_meta: list[dict] = []

    for idx, step in enumerate(plan):
        agent_name = step["agent"]
        subtask = step["subtask"]
        agent_cfg = AGENTS[agent_name]

        yield {
            "event": "agent_phase",
            "data": json.dumps({"phase": "running", "index": idx, "agent": agent_name, "subtask": subtask}),
        }

        sub_answer_chunks: list[str] = []
        sub_meta: list[dict] = []

        sub_mode = agent_cfg.get("default_mode") or "deep"
        sub_focus = agent_cfg.get("default_focus") or focus

        async for evt in run_deep_research(
            subtask,
            history=[],
            mode=sub_mode,
            focus=sub_focus,
            doc_ids=doc_ids,
            agent=agent_name,
        ):
            ev = evt["event"]
            if ev == "token":
                sub_answer_chunks.append(evt["data"])
            elif ev == "sources":
                try:
                    sub_meta = json.loads(evt["data"])
                except Exception:
                    sub_meta = []
            elif ev == "step":
                yield {
                    "event": "sub_step",
                    "data": json.dumps({"sub_index": idx, **json.loads(evt["data"])}),
                }
            elif ev == "step_result":
                yield {
                    "event": "sub_step_result",
                    "data": json.dumps({"sub_index": idx, **json.loads(evt["data"])}),
                }
            elif ev == "error":
                yield {
                    "event": "sub_error",
                    "data": json.dumps({"sub_index": idx, "agent": agent_name, "error": evt["data"]}),
                }

        # Re-number this sub-agent's sources into the unified list.
        local_map: dict[int, int] = {}
        for src in sub_meta:
            local_n = src.get("n")
            global_n = len(unified_meta) + 1
            local_map[local_n] = global_n
            unified_meta.append({**src, "n": global_n, "source_agent": agent_name})

        sub_answer_text = "".join(sub_answer_chunks).strip()

        def _rewrite(m, lm=local_map):
            n = int(m.group(1))
            return f"[{lm.get(n, n)}]"
        rewritten = re.sub(r"\[(\d+)\]", _rewrite, sub_answer_text)

        sub_results.append({
            "agent": agent_name,
            "subtask": subtask,
            "answer": rewritten,
            "raw_answer": sub_answer_text,
        })

        yield {
            "event": "agent_phase",
            "data": json.dumps({"phase": "done", "index": idx, "agent": agent_name}),
        }

    # Emit the unified source list for the UI.
    yield {"event": "sources", "data": json.dumps(unified_meta)}

    # Synthesis call — stream tokens.
    yield {"event": "agent_phase", "data": json.dumps({"phase": "synthesizing"})}

    synth_user = (
        "Original question:\n"
        f"{query}\n\n"
        "Specialist sub-answers (citations already renumbered to the unified list below):\n\n"
        + "\n\n".join(
            f"### {r['agent'].title()} — {r['subtask']}\n{r['answer']}"
            for r in sub_results
        )
        + "\n\nUnified source list:\n"
        + "\n".join(f"[{s['n']}] {s.get('title','')} — {s.get('url','')}" for s in unified_meta)
    )
    try:
        stream = await llm.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": ORCHESTRATOR_SYNTH_PROMPT},
                *history,
                {"role": "user", "content": synth_user},
            ],
            temperature=0.3,
            max_tokens=2048,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                delta = delta.replace("【", "[").replace("】", "]")
                yield {"event": "token", "data": delta}
    except Exception as e:
        yield {"event": "error", "data": f"Synthesizer error: {e}"}
