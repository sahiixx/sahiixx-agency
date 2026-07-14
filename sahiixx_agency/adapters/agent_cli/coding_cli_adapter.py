"""Coding-agent CLI adapter (generic).

Connects coding-agent CLIs (qwen-code, gemini-cli, codex, ...) to the execution
pipeline. Runs the agent binary with a brief when installed, otherwise returns a
deterministic simulation so the dispatch chain stays green offline.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy


@dataclass
class CodingCliResult:
    ok: bool
    brief: str
    command: str
    returncode: int
    stdout: str
    stderr: str
    cwd: str
    status: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.status:
            self.status = "success" if self.ok else "failed"


class CodingAgentCliAdapter:
    """Adapter that runs a coding-agent CLI from a brief."""

    def __init__(
        self,
        binary: str,
        timeout: int = 600,
        fallback_on_failure: bool = True,
        network_policy: NetworkPolicy | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.binary = binary
        self.timeout = timeout
        self.fallback_on_failure = fallback_on_failure
        self.network_policy = network_policy
        self.audit_logger = audit_logger

    def _check_network_policy(self, node: RepoNode) -> None:
        policy = self.network_policy
        if policy is None or policy.allow_all:
            return
        hosts = node.external_hosts or []
        if not hosts:
            return
        blocked = [host for host in hosts if not policy.is_allowed(host)]
        if blocked:
            message = (
                f"Network policy blocks outbound hosts for module {node.full_name}: "
                f"{', '.join(blocked)}"
            )
            if self.audit_logger is not None:
                self.audit_logger.log(
                    "network_policy_violation",
                    "CodingAgentCliAdapter",
                    node.id,
                    {"blocked_hosts": blocked, "allowlist": sorted(policy.allowlist)},
                )
            raise RuntimeError(message)

    def _run_subprocess(self, command: list[str]) -> CodingCliResult:
        command_str = " ".join(command)
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            return CodingCliResult(
                ok=proc.returncode == 0,
                brief="",
                command=command_str,
                returncode=proc.returncode,
                stdout=proc.stdout[:8000] if proc.stdout else "",
                stderr=proc.stderr[:4000] if proc.stderr else "",
                cwd=os.getcwd(),
                status="success" if proc.returncode == 0 else "error",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except subprocess.TimeoutExpired as exc:
            return CodingCliResult(
                ok=False, brief="", command=command_str, returncode=-1,
                stdout=str(exc.stdout or ""), stderr=f"Timeout after {self.timeout}s",
                cwd=os.getcwd(), status="timeout",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except Exception as exc:  # noqa: BLE001
            return CodingCliResult(
                ok=False, brief="", command=command_str, returncode=-1,
                stdout="", stderr=str(exc), cwd=os.getcwd(), status="exception",
                metadata={"timeout": self.timeout, "fallback": False},
            )

    def _simulate(self, brief: str) -> CodingCliResult:
        return CodingCliResult(
            ok=True,
            brief=brief,
            command=f"{self.binary} <brief> <simulated>",
            returncode=0,
            stdout=(
                f"[SIMULATED] {self.binary} coding-agent session\n"
                f"brief: {brief}\n"
                f"next_step: install {self.binary} and run `{self.binary} \"{brief}\"`\n"
            ),
            stderr="",
            cwd=os.getcwd(),
            status="simulated",
            metadata={"timeout": self.timeout, "fallback": True, "note": f"{self.binary} not found"},
        )

    def dispatch(self, brief: str) -> CodingCliResult:
        if not brief:
            return CodingCliResult(
                ok=False, brief="", command="", returncode=-1, stdout="",
                stderr="No brief provided", cwd=os.getcwd(), status="failed",
            )
        bin_path = shutil.which(self.binary)
        if bin_path is None:
            return self._simulate(brief)

        command = [bin_path, brief]
        result = self._run_subprocess(command)
        if not result.ok and self.fallback_on_failure:
            simulated = self._simulate(brief)
            simulated.metadata["original_error"] = result.stderr[:500]
            return simulated
        return result

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        self._check_network_policy(node)
        brief = payload.get("brief") or payload.get("intent") or ""
        result = self._simulate(brief) if payload.get("simulate") else self.dispatch(brief=brief)
        return result.metadata | {
            "module": node.name,
            "status": result.status,
            "brief": result.brief,
            "command": result.command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": result.cwd,
        }


def _make_coding_cli(binary: str):
    def _factory(config, network_policy, audit_logger, task):
        from sahiixx_agency.adapters.agent_cli.coding_cli_adapter import (
            CodingAgentCliAdapter,
        )

        adapter = CodingAgentCliAdapter(
            binary=binary,
            network_policy=network_policy,
            audit_logger=audit_logger,
        )
        payload = dict(task.payload)
        payload.setdefault("brief", task.intent)
        return adapter, payload

    return _factory
