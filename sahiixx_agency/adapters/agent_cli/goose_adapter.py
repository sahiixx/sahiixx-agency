"""Goose adapter.

Connects the promoted ``goose`` ecosystem module (extensible AI agent) to the
execution pipeline. Runs the Goose CLI when present, otherwise returns a
deterministic simulation so the dispatch chain stays green offline.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy

DEFAULT_CLONE_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "repos")
)


@dataclass
class GooseResult:
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


class GooseAdapter:
    """Adapter that runs a Goose agent session from a brief."""

    def __init__(
        self,
        repo_dir: str | Path | None = None,
        clone_base_dir: str | Path | None = None,
        timeout: int = 300,
        fallback_on_failure: bool = True,
        network_policy: NetworkPolicy | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        base = Path(clone_base_dir) if clone_base_dir else Path(DEFAULT_CLONE_BASE)
        self.repo_dir = Path(repo_dir) if repo_dir else base / "goose"
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
                    "GooseAdapter",
                    node.id,
                    {"blocked_hosts": blocked, "allowlist": sorted(policy.allowlist)},
                )
            raise RuntimeError(message)

    def _run_subprocess(self, command: list[str]) -> GooseResult:
        command_str = " ".join(command)
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            return GooseResult(
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
            return GooseResult(
                ok=False, brief="", command=command_str, returncode=-1,
                stdout=str(exc.stdout or ""), stderr=f"Timeout after {self.timeout}s",
                cwd=os.getcwd(), status="timeout",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except Exception as exc:  # noqa: BLE001
            return GooseResult(
                ok=False, brief="", command=command_str, returncode=-1,
                stdout="", stderr=str(exc), cwd=os.getcwd(), status="exception",
                metadata={"timeout": self.timeout, "fallback": False},
            )

    def _simulate(self, brief: str) -> GooseResult:
        return GooseResult(
            ok=True,
            brief=brief,
            command="goose run -t <brief> <simulated>",
            returncode=0,
            stdout=(
                f"[SIMULATED] Goose agent session\n"
                f"brief: {brief}\n"
                f"next_step: install goose (https://github.com/aaif-goose/goose) && "
                f"goose run -t \"{brief}\"\n"
            ),
            stderr="",
            cwd=os.getcwd(),
            status="simulated",
            metadata={"timeout": self.timeout, "fallback": True, "note": "goose CLI not found"},
        )

    def dispatch(self, brief: str) -> GooseResult:
        if not brief:
            return GooseResult(
                ok=False, brief="", command="", returncode=-1, stdout="",
                stderr="No brief provided", cwd=os.getcwd(), status="failed",
            )
        goose_bin = shutil.which("goose")
        if goose_bin is None:
            return self._simulate(brief)

        command = [goose_bin, "run", "-t", brief]
        result = self._run_subprocess(command)
        if not result.ok and self.fallback_on_failure:
            simulated = self._simulate(brief)
            simulated.metadata["original_error"] = result.stderr[:500]
            return simulated
        return result

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        self._check_network_policy(node)
        brief = payload.get("brief") or payload.get("intent") or ""
        result = self.dispatch(brief=brief)
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


def _make_goose(config, network_policy, audit_logger, task):
    from sahiixx_agency.adapters.agent_cli.goose_adapter import GooseAdapter

    adapter = GooseAdapter(
        clone_base_dir=os.path.join(config.data_dir, "repos"),
        network_policy=network_policy,
        audit_logger=audit_logger,
    )
    payload = dict(task.payload)
    payload.setdefault("brief", task.intent)
    return adapter, payload
