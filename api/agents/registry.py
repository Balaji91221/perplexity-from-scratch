"""Agent presets — the multi-agent registry.

Each entry is a small declarative config. The Orchestrator is just a marker;
its actual logic lives in `agents/orchestrator.py`.
"""

from typing import Optional

from .prompts import ANALYST_PROMPT, CODER_PROMPT, RESEARCHER_PROMPT


AGENTS: dict[str, dict] = {
    "generalist": {
        "label": "Generalist",
        "blurb": "Balanced answer engine — picks tools as needed.",
        "system_prompt": None,             # use mode-default prompt
        "tool_whitelist": None,            # all tools allowed
        "default_mode": "quick",
        "default_focus": "web",
    },
    "researcher": {
        "label": "Researcher",
        "blurb": "Deep, citation-heavy research with academic priors.",
        "system_prompt": RESEARCHER_PROMPT,
        "tool_whitelist": {"search", "read_url", "browse_url", "read_doc"},
        "default_mode": "deep",
        "default_focus": "academic",
    },
    "coder": {
        "label": "Coder",
        "blurb": "Working code first, prose second.",
        "system_prompt": CODER_PROMPT,
        "tool_whitelist": {"search", "read_url", "read_doc"},
        "default_mode": "deep",
        "default_focus": "web",
    },
    "analyst": {
        "label": "Analyst",
        "blurb": "Tidy tables and structured extraction from sources.",
        "system_prompt": ANALYST_PROMPT,
        "tool_whitelist": {"read_doc", "search", "read_url"},
        "default_mode": "deep",
        "default_focus": "web",
    },
    "orchestrator": {
        "label": "Orchestrator",
        "blurb": "Decomposes the question and routes to specialist agents.",
        "system_prompt": None,
        "tool_whitelist": None,
        "default_mode": "deep",
        "default_focus": "web",
        "is_orchestrator": True,
    },
}


def resolve_agent(name: Optional[str]) -> dict:
    return AGENTS.get(name or "generalist", AGENTS["generalist"])
