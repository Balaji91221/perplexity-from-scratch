"""GET /mcp/servers — list MCP servers we tried to connect, plus their tools."""

from fastapi import APIRouter

from mcp_hub import hub as mcp_hub

router = APIRouter()


@router.get("/mcp/servers")
def mcp_servers():
    return mcp_hub.status_for_api()
