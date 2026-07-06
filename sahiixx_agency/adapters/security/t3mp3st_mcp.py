"""MCP-native adapter for T3MP3ST with subprocess fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from sahiixx_agency.adapters.security.t3mp3st import T3mp3stAdapter
from sahiixx_agency.core.models import RepoNode

ClientSession: Any
StdioServerParameters: Any
stdio_client: Any

try:
    from mcp import ClientSession as _ClientSession
    from mcp import StdioServerParameters as _StdioServerParameters
    from mcp import stdio_client as _stdio_client
except ImportError:  # pragma: no cover - fallback if mcp not installed
    ClientSession = None
    StdioServerParameters = None
    stdio_client = None
else:
    ClientSession = _ClientSession
    StdioServerParameters = _StdioServerParameters
    stdio_client = _stdio_client


class T3mp3stMcpAdapter(T3mp3stAdapter):
    """Adapter that invokes T3MP3ST via MCP, falling back to subprocess."""

    def __init__(
        self,
        clone_base_dir: str = "./data/repos",
        approval_token: str | None = None,
        tool_name: str | None = None,
    ) -> None:
        super().__init__(clone_base_dir=clone_base_dir, approval_token=approval_token)
        self.tool_name = tool_name

    def _find_mcp_server_script(self, repo_path: Path) -> list[str] | None:
        """Discover the MCP server entrypoint inside the cloned repo."""
        repo_root = repo_path.resolve()

        def _safe_script_path(rel_path: str) -> Path | None:
            candidate = (repo_path / rel_path).resolve()
            try:
                candidate.relative_to(repo_root)
            except ValueError:
                return None
            return candidate if candidate.exists() else None

        package_json = repo_path / "package.json"
        if package_json.exists():
            with open(package_json, encoding="utf-8") as f:
                pkg = json.load(f)
            bin_field = pkg.get("bin")
            if isinstance(bin_field, dict):
                for name, rel_path in bin_field.items():
                    if "mcp" in name.lower() or "server" in name.lower():
                        script_path = _safe_script_path(str(rel_path))
                        if script_path is not None:
                            return ["node", str(script_path)]
            if isinstance(bin_field, str):
                script_path = _safe_script_path(bin_field)
                if script_path is not None:
                    return ["node", str(script_path)]

        for candidate in [
            "dist/mcp-server.js",
            "build/mcp-server.js",
            "lib/mcp-server.js",
            "mcp-server.js",
            "dist/index.js",
            "build/index.js",
        ]:
            script_path = _safe_script_path(candidate)
            if script_path is not None:
                return ["node", str(script_path)]
        return None

    def _pick_tool(self, tools: list[dict[str, Any]]) -> str | None:
        if self.tool_name:
            return self.tool_name
        names = [str(t.get("name", "")) for t in tools]
        for name in names:
            if "recon" in name.lower():
                return name
        for name in names:
            if "security" in name.lower() or "scan" in name.lower():
                return name
        return names[0] if names else None

    async def run(self, module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        blocked_networks = module.adapter_config.get("blocked_targets")
        env, error = self._validate_payload(
            payload,
            blocked_networks=blocked_networks,
            allow_local=module.adapter_config.get("allow_local"),
        )
        if error:
            return error

        assert env is not None

        if stdio_client is None or ClientSession is None or StdioServerParameters is None:
            return await self._fallback(module, payload, reason="mcp_sdk_unavailable")

        try:
            path = await self.runner.clone_manager.clone(module)
        except Exception as exc:
            return await self._fallback(module, payload, reason="clone_failed", error=str(exc))

        server_cmd = self._find_mcp_server_script(path)
        if server_cmd is None:
            return await self._fallback(module, payload, reason="mcp_server_not_found")

        run_env = {**os.environ, **env}
        params = StdioServerParameters(
            command=server_cmd[0],
            args=server_cmd[1:],
            env=run_env,
        )

        try:
            async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
                await session.initialize()
                tools_result = await session.list_tools()
                tools = [
                    t.model_dump() if hasattr(t, "model_dump") else dict(t)
                    for t in tools_result.tools
                ]
                tool_name = self._pick_tool(tools)
                if tool_name is None:
                    return await self._fallback(module, payload, reason="no_matching_mcp_tool")

                result = await session.call_tool(
                    tool_name,
                    arguments={
                        "target": payload["target"],
                        "mode": payload.get("mode", "lite"),
                        "approval": payload.get("approval"),
                    },
                )
                return {
                    "status": "success",
                    "source": "mcp",
                    "tool": tool_name,
                    "t3mp3st_mode": payload.get("mode", "lite"),
                    "t3mp3st_target": payload["target"],
                    "result": result.model_dump() if hasattr(result, "model_dump") else dict(result),
                }
        except Exception as exc:
            return await self._fallback(module, payload, reason="mcp_error", error=str(exc))

    async def _fallback(
        self,
        module: RepoNode,
        payload: dict[str, Any],
        reason: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        result = await super().run(module, payload)
        result["source"] = "subprocess"
        result["fallback_reason"] = reason
        if error:
            result["fallback_error"] = error
        return result
