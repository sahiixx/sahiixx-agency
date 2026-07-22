"""HTTP MCP client adapter — connects OPA to a remote MCP server over Streamable HTTP.

This is what makes OPA actually *use* (not just discover) an MCP server registered
in agency.yaml with a ``mcp_endpoint`` field. The previous McpAdapter stub only
cloned/ran repos and never touched ``mcp_endpoint``, so MCP modules were metadata-only.

Uses the official ``mcp`` Python SDK's ``streamablehttp_client`` + ``ClientSession``.
The f worker exposes exactly this transport at http://localhost:8787/mcp.

Protocol note: the worker's hand-rolled MCP server speaks JSON-RPC 2024-11-05 and
returns a plain JSON body, which the streamablehttp client accepts.
"""
from __future__ import annotations

import json
import os
from typing import Any

from sahiixx_agency.adapters.base import BaseAdapter
from sahiixx_agency.core.models import RepoNode


class HttpMcpAdapter(BaseAdapter):
    """Connect to a remote MCP server over HTTP and execute a tool call."""

    async def run(self, module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        cfg = module.adapter_config or {}
        endpoint = cfg.get("mcp_endpoint") or (module.manifest or {}).get("mcp_endpoint")
        if not endpoint:
            # Some ecosystem entries put mcp_endpoint at the top level of the yaml stub.
            endpoint = os.environ.get("F_WORKER_MCP_ENDPOINT", "http://localhost:8787/mcp")
        tool_name = payload.get("tool") or payload.get("tool_name")
        tool_args = payload.get("tool_args") or payload.get("arguments") or {}
        if not tool_name:
            return {
                "status": "error",
                "error": "HttpMcpAdapter requires payload['tool'] (and optional payload['tool_args'])",
            }
        return await self._call(endpoint, tool_name, tool_args)

    async def _call(self, endpoint: str, tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        # streamablehttp_client is an async context manager yielding (read, write, get_session_id)
        async with streamablehttp_client(endpoint) as (read, write, _get_session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, tool_args)
                # Flatten MCP content blocks into text
                parts = []
                for item in getattr(result, "content", []) or []:
                    text = getattr(item, "text", None)
                    if text is not None:
                        parts.append(text)
                structured = None
                if len(parts) == 1:
                    try:
                        structured = json.loads(parts[0])
                    except (json.JSONDecodeError, TypeError):
                        structured = None
                return {
                    "status": "completed",
                    "module": "f-worker-ai",
                    "tool": tool_name,
                    "endpoint": endpoint,
                    "result": structured if structured is not None else "\n".join(parts),
                    "is_error": bool(getattr(result, "isError", False)),
                }


def run_mcp_http(module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
    """Synchronous helper mirroring run_mcp_module in runner.py."""
    import asyncio

    return asyncio.run(HttpMcpAdapter().run(module, payload))
