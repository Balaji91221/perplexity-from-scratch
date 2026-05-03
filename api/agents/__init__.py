"""Agentic layer.

prompts.py        — system prompts (Quick / Deep / Computer / per-specialist / orchestrator)
registry.py       — AGENTS dict (Generalist, Researcher, Coder, Analyst, Orchestrator) + resolve_agent
tools.py          — tool implementations (search/read_url/browse_url/read_doc), schemas, dispatch table
deep_research.py  — single-agent tool-call loop (Quick is in routes/ask.py — it's a one-shot)
orchestrator.py   — multi-agent: planner → specialists → synthesizer
"""

from .registry import AGENTS, resolve_agent  # noqa: F401
from .deep_research import run_deep_research  # noqa: F401
from .orchestrator import run_orchestrator    # noqa: F401
