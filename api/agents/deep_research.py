"""Single-agent tool-calling loop.

Streams SSE events:
  step          — agent decided to call a tool
  step_result   — tool finished, result attached
  sources       — final source list (numbered)
  token         — answer tokens
  error         — anything that went wrong
"""

import json
from typing import Optional

from config import DEEP_MAX_STEPS, MAX_CHARS_PER_SOURCE, MODEL
from llm import llm
from mcp_hub import hub as mcp_hub

from .prompts import COMPUTER_SYSTEM_PROMPT, DEEP_SYSTEM_PROMPT
from .registry import resolve_agent
from .tools import (
    collected_to_meta,
    make_tool_impls,
    make_tools_schema,
    title_from_search_results,
)


async def run_deep_research(
    query: str,
    history: list[dict],
    mode: str = "deep",
    focus: str = "web",
    doc_ids: Optional[list[str]] = None,
    agent: str = "generalist",
):
    """Async generator yielding SSE event dicts."""
    doc_ids = doc_ids or []
    cfg = resolve_agent(agent)

    # Base prompt comes from the mode, overridden by the agent's persona prompt if present.
    base_prompt = COMPUTER_SYSTEM_PROMPT if mode == "computer" else DEEP_SYSTEM_PROMPT
    system_prompt = cfg["system_prompt"] or base_prompt

    if doc_ids:
        system_prompt += (
            "\n\nThe user has attached one or more PDF documents. "
            "If the question is about those documents, call read_doc(query) first — "
            "the matching passages will appear in the conversation as sources."
        )
    mcp_tool_count = sum(len(s["tools"]) for s in mcp_hub.servers.values() if s["status"] == "ok")
    if mcp_tool_count:
        system_prompt += (
            f"\n\nYou also have access to {mcp_tool_count} additional MCP tools "
            f"(prefixed with mcp_<server>__<tool>). Their descriptions explain their use. "
            f"Prefer them when their description matches the user's intent — e.g., a question about "
            f"the current time should use mcp_time__* over a web search."
        )

    tool_impls = make_tool_impls(mode, focus=focus, doc_ids=doc_ids)
    tools_schema = make_tools_schema(doc_ids=doc_ids, agent=agent)

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": query},
    ]

    collected: list[dict] = []
    seen_urls: set[str] = set()
    search_log: list[dict] = []

    for step in range(DEEP_MAX_STEPS):
        try:
            resp = await llm.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools_schema,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=2048,
            )
        except Exception as e:
            yield {"event": "error", "data": f"LLM error in planning step {step+1}: {e}"}
            return

        choice = resp.choices[0].message
        tool_calls = choice.tool_calls or []

        # No tool calls → the model is ready to answer.
        if not tool_calls:
            answer = (choice.content or "").replace("【", "[").replace("】", "]").strip()
            meta = [collected_to_meta(s) for s in collected]
            yield {"event": "sources", "data": json.dumps(meta)}
            chunk = 24
            for i in range(0, len(answer), chunk):
                yield {"event": "token", "data": answer[i : i + chunk]}
            yield {"event": "final_answer", "data": answer}
            return

        # Append the assistant message with its tool calls (required by the API contract).
        messages.append(
            {
                "role": "assistant",
                "content": choice.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in tool_calls
                ],
            }
        )

        for tc in tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            yield {
                "event": "step",
                "data": json.dumps({"step": step + 1, "tool": name, "args": args}),
            }

            impl = tool_impls.get(name)
            if impl is not None:
                tool_text, ui_payload = await impl(args)
            elif mcp_hub.is_mcp_tool(name):
                tool_text, ui_payload = await mcp_hub.call(name, args)
            else:
                tool_text = f"Unknown tool: {name}"
                ui_payload = {"error": tool_text}

            # Track sources we successfully read.
            if name == "search":
                search_log.append(ui_payload)
            elif name in ("read_url", "browse_url") and ui_payload.get("ok"):
                url = ui_payload["url"]
                if url not in seen_urls:
                    seen_urls.add(url)
                    title = ui_payload.get("title") or title_from_search_results(url, search_log)
                    body = tool_text.split("\n\n", 1)[1] if "\n\n" in tool_text else tool_text
                    collected.append(
                        {"n": len(collected) + 1, "url": url, "title": title, "text": body[:MAX_CHARS_PER_SOURCE]}
                    )
            elif name == "read_doc":
                for r in ui_payload.get("_rows", []) or []:
                    chunk_url = f"document://{r['document_id']}#chunk-{r['chunk_index']}"
                    if chunk_url in seen_urls:
                        continue
                    seen_urls.add(chunk_url)
                    collected.append({
                        "n": len(collected) + 1,
                        "type": "doc",
                        "url": chunk_url,
                        "title": f"{r['filename']} — Page {r['page']}" if r.get("page") else r["filename"],
                        "doc_id": r["document_id"],
                        "page": r.get("page"),
                        "filename": r["filename"],
                        "text": r["content"][:MAX_CHARS_PER_SOURCE],
                    })

            # Strip large internal payloads before sending to the client.
            ui_for_client = {k: v for k, v in ui_payload.items() if not k.startswith("_")}
            yield {
                "event": "step_result",
                "data": json.dumps({"step": step + 1, "tool": name, "result": ui_for_client}),
            }

            # Append the tool response message for the next planning iteration.
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_text,
                }
            )

        # Inject the running citation map so the model knows what numbers to use.
        if collected:
            cite_block = "Citation map (use these numbers in your final answer):\n" + "\n".join(
                f"[{s['n']}] {s['title']} — {s['url']}" for s in collected
            )
            messages.append({"role": "system", "content": cite_block})

    # Hit step cap without a final answer; force one.
    if collected:
        meta = [collected_to_meta(s) for s in collected]
        yield {"event": "sources", "data": json.dumps(meta)}
        messages.append(
            {
                "role": "user",
                "content": "Time is up — write the final answer now using only the citation map. ASCII [N] brackets only.",
            }
        )
        try:
            stream = await llm.chat.completions.create(
                model=MODEL, messages=messages, temperature=0.2, max_tokens=2048, stream=True
            )
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    delta = delta.replace("【", "[").replace("】", "]")
                    yield {"event": "token", "data": delta}
        except Exception as e:
            yield {"event": "error", "data": f"LLM error in finalizer: {e}"}
    else:
        yield {
            "event": "token",
            "data": "I couldn't gather enough information to answer confidently within the step budget.",
        }
