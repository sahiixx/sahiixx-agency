"""Generic adapter that runs any repo using an inferred or supplied command."""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.discovery.entrypoint import infer_entrypoint


class GenericAdapter:
    """Run any registered module by detecting its entrypoint."""

    def __init__(
        self,
        data_dir: str = "./data",
        timeout: int = 120,
        fallback_on_failure: bool = True,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.timeout = timeout
        self.fallback_on_failure = fallback_on_failure

    def _repo_dir(self, node: RepoNode) -> Path | None:
        candidates = [
            self.data_dir / "repos" / node.name,
            self.data_dir / "repos" / "trending" / node.owner / node.name,
            self.data_dir / "repos" / node.owner / node.name,
            self.data_dir / node.name,
        ]
        if node.local_path:
            candidates.insert(0, Path(node.local_path))
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _build_command(self, node: RepoNode, payload: dict[str, Any]) -> list[str] | None:
        raw_command = payload.get("command")
        if isinstance(raw_command, str):
            return raw_command.split()
        repo_dir = self._repo_dir(node)
        if repo_dir:
            entrypoint = infer_entrypoint(repo_dir)
            if entrypoint:
                return entrypoint
        return None

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        repo_dir = self._repo_dir(node)
        if repo_dir is None:
            return self._simulate(node, payload, reason="repo not cloned")

        command = self._build_command(node, payload)
        if command is None:
            return self._simulate(node, payload, reason="no entrypoint inferred")

        run_env = {**os.environ, **(payload.get("env") or {})}
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                command,
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                timeout=payload.get("timeout", self.timeout),
                env=run_env,
                check=False,
            )
            ok = proc.returncode == 0
            if not ok and self.fallback_on_failure:
                return self._simulate(node, payload, reason=f"exit code {proc.returncode}", stderr=proc.stderr[:500])
            return {
                "module": node.name,
                "status": "success" if ok else "error",
                "command": " ".join(command),
                "returncode": proc.returncode,
                "stdout": proc.stdout[:8000],
                "stderr": proc.stderr[:4000],
                "repo_dir": str(repo_dir),
            }
        except subprocess.TimeoutExpired:
            return self._simulate(node, payload, reason="timeout") if self.fallback_on_failure else {
                "module": node.name,
                "status": "timeout",
                "command": " ".join(command),
                "error": f"Timeout after {self.timeout}s",
            }
        except Exception as exc:  # noqa: BLE001
            return self._simulate(node, payload, reason=str(exc)) if self.fallback_on_failure else {
                "module": node.name,
                "status": "exception",
                "error": str(exc),
            }

    def _simulate(self, node: RepoNode, payload: dict[str, Any], reason: str, stderr: str = "") -> dict[str, Any]:
        return {
            "module": node.name,
            "status": "simulated",
            "command": payload.get("command") or "<inferred>",
            "stdout": f"[SIMULATED] Would run {node.full_name} with payload {payload}",
            "stderr": stderr or f"Fallback because: {reason}",
            "repo_dir": node.local_path or "",
            "fallback": True,
        }
