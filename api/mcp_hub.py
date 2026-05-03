"""
MCP (Model Context Protocol) hub.

Spawns one stdio MCP server per configured entry, holds long-lived sessions,
discovers tools, and exposes them in OpenAI tool-call format so the agent loop
can invoke them. Tool names are namespaced as `mcp_<server>__<tool>` to avoid
collisions with our built-in tools.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import AsyncExitStack
from typing import Any, Optional

logger = logging.getLogger("mcp_hub")

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
    _MCP_IMPORT_ERR: Optional[str] = None
except Exception as e:  # pragma: no cover
    MCP_AVAILABLE = False
    _MCP_IMPORT_ERR = str(e)


# Default servers — can be extended later via config. These are official
# Anthropic reference servers that ship as pip packages, so they boot in our
# api container with no extra system deps.
DEFAULT_SERVERS: list[dict[str, Any]] = [
    {
        "name": "time",
        "command": "python",
        "args": ["-m", "mcp_server_time", "--local-timezone=UTC"],
        "description": "Get current time in any timezone, convert between zones.",
    },
    {
        "name": "fetch",
        "command": "python",
        "args": ["-m", "mcp_server_fetch"],
        "description": "Fetch a URL and return its readable content.",
    },
]


class McpHub:
    def __init__(self):
        self.servers: dict[str, dict[str, Any]] = {}
        self._stack = AsyncExitStack()
        self._lock = asyncio.Lock()

    async def start(self, servers: list[dict[str, Any]] | None = None):
        """Connect to each configured server. Failures are recorded but don't crash startup."""
        if not MCP_AVAILABLE:
            logger.warning("MCP SDK not available: %s", _MCP_IMPORT_ERR)
            for cfg in (servers or DEFAULT_SERVERS):
                self.servers[cfg["name"]] = {
                    "status": "error",
                    "error": f"mcp SDK not installed: {_MCP_IMPORT_ERR}",
                    "tools": [],
                    "description": cfg.get("description", ""),
                }
            return

        for cfg in (servers or DEFAULT_SERVERS):
            await self._connect(cfg)

    async def _connect(self, cfg: dict[str, Any]):
        name = cfg["name"]
        try:
            params = StdioServerParameters(
                command=cfg["command"],
                args=cfg.get("args", []),
                env=cfg.get("env"),
            )
            read, write = await self._stack.enter_async_context(stdio_client(params))
            session = await self._stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            tools_resp = await session.list_tools()
            tools = []
            for t in tools_resp.tools:
                tools.append({
                    "name": t.name,
                    "description": (t.description or t.name or "").strip(),
                    "schema": t.inputSchema or {"type": "object", "properties": {}},
                })
            self.servers[name] = {
                "status": "ok",
                "session": session,
                "tools": tools,
                "description": cfg.get("description", ""),
            }
            logger.info("MCP connected: %s (%d tools)", name, len(tools))
        except Exception as e:
            logger.warning("MCP server %s failed to connect: %s", name, e)
            self.servers[name] = {
                "status": "error",
                "error": str(e),
                "tools": [],
                "description": cfg.get("description", ""),
            }

    def list_tool_schemas(self) -> list[dict]:
        """OpenAI-style tool schemas for every connected MCP tool."""
        out = []
        for srv_name, info in self.servers.items():
            if info["status"] != "ok":
                continue
            for t in info["tools"]:
                desc = t["description"] or t["name"]
                out.append({
                    "type": "function",
                    "function": {
                        "name": f"mcp_{srv_name}__{t['name']}",
                        "description": f"[{srv_name}] {desc}",
                        "parameters": t["schema"],
                    },
                })
        return out

    def is_mcp_tool(self, name: str) -> bool:
        return name.startswith("mcp_")

    def parse_tool(self, prefixed: str) -> tuple[str, str]:
        if not prefixed.startswith("mcp_"):
            raise ValueError(f"not an mcp tool: {prefixed}")
        rest = prefixed[len("mcp_"):]
        srv, _, tool = rest.partition("__")
        return srv, tool

    async def call(self, prefixed_name: str, args: dict) -> tuple[str, dict]:
        """Call an MCP tool. Returns (text_for_LLM, ui_payload)."""
        try:
            srv_name, tool_name = self.parse_tool(prefixed_name)
        except ValueError as e:
            return f"Invalid MCP tool name: {e}", {"error": str(e)}

        info = self.servers.get(srv_name)
        if not info or info["status"] != "ok":
            err = (info or {}).get("error", "not connected")
            return f"MCP server '{srv_name}' is not available: {err}", {"server": srv_name, "error": err}

        try:
            async with self._lock:
                result = await info["session"].call_tool(tool_name, arguments=args)
        except Exception as e:
            return f"MCP call failed: {e}", {"server": srv_name, "tool": tool_name, "error": str(e)}

        # Flatten content to text.
        parts = []
        for c in (result.content or []):
            if hasattr(c, "text") and c.text is not None:
                parts.append(c.text)
            elif hasattr(c, "data") and c.data is not None:
                parts.append(f"[binary data: {len(c.data)} bytes]")
        text = "\n".join(parts) if parts else "(no content)"
        is_error = bool(getattr(result, "isError", False))
        return text, {
            "server": srv_name,
            "tool": tool_name,
            "ok": not is_error,
            "preview": text[:240],
        }

    def status_for_api(self) -> list[dict]:
        out = []
        for name, info in self.servers.items():
            entry = {
                "name": name,
                "status": info["status"],
                "description": info.get("description", ""),
                "tools": [{"name": t["name"], "description": t["description"]} for t in info["tools"]],
            }
            if info["status"] == "error":
                entry["error"] = info.get("error", "unknown")
            out.append(entry)
        return out

    async def close(self):
        try:
            await self._stack.aclose()
        except Exception as e:
            logger.warning("Error closing MCP hub: %s", e)


hub = McpHub()
