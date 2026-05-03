"""GET /agents — public agent registry that drives the frontend agent picker."""

from fastapi import APIRouter

from agents.registry import AGENTS

router = APIRouter()


@router.get("/agents")
def agents_list():
    return [
        {
            "key": key,
            "label": cfg["label"],
            "blurb": cfg["blurb"],
            "default_mode": cfg.get("default_mode"),
            "default_focus": cfg.get("default_focus"),
            "is_orchestrator": bool(cfg.get("is_orchestrator")),
        }
        for key, cfg in AGENTS.items()
    ]
