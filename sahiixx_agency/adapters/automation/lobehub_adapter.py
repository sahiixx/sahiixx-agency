"""LobeHub automation adapter.

Connects the promoted ``lobehub`` ecosystem module to the execution pipeline.
LobeHub is an "AI agent operator" that hires, schedules, and reports on an AI
team. The adapter scaffolds an agent-team manifest from a brief and optionally
POSTs it to a reachable LobeHub server, otherwise returns a deterministic
simulation so the dispatch chain stays green offline.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy

DEFAULT_LOBEHUB_BASE = "http://localhost:3210/api"


@dataclass
class LobeHubResult:
    ok: bool
    brief: str
    command: str
    returncode: int
    stdout: str
    stderr: str
    cwd: str
    manifest_path: str = ""
    status: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.status:
            self.status = "success" if self.ok else "failed"


class LobeHubAdapter:
    """Adapter that scaffolds / dispatches a LobeHub agent team from a brief."""

    def __init__(
        self,
        base_url: str = DEFAULT_LOBEHUB_BASE,
        network_policy: NetworkPolicy | None = None,
        audit_logger: AuditLogger | None = None,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.network_policy = network_policy
        self.audit_logger = audit_logger
        self.timeout = timeout

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
                    "LobeHubAdapter",
                    node.id,
                    {"blocked_hosts": blocked, "allowlist": sorted(policy.allowlist)},
                )
            raise RuntimeError(message)

    def _build_manifest(self, brief: str) -> dict[str, Any]:
        return {
            "team": "".join(c if c.isalnum() else " " for c in brief[:40]).strip(),
            "brief": brief,
            "agents": [
                {"role": "researcher", "instruction": f"Research: {brief}"},
                {"role": "operator", "instruction": f"Execute: {brief}"},
                {"role": "reporter", "instruction": f"Report results for: {brief}"},
            ],
        }

    def _write_manifest(self, project_dir: Path, brief: str) -> Path:
        project_dir.mkdir(parents=True, exist_ok=True)
        path = project_dir / "team.json"
        path.write_text(json.dumps(self._build_manifest(brief), indent=2), encoding="utf-8")
        return path

    def _simulate(self, project_dir: Path, brief: str) -> LobeHubResult:
        path = self._write_manifest(project_dir, brief)
        return LobeHubResult(
            ok=True,
            brief=brief,
            command="POST /agent-teams <simulated>",
            returncode=0,
            stdout=(
                f"[SIMULATED] LobeHub agent team scaffolded at {path}\n"
                f"next_step: start LobeHub and import {path}, or POST to "
                f"{self.base_url}/agent-teams\n"
            ),
            stderr="",
            cwd=str(project_dir),
            manifest_path=str(path),
            status="simulated",
            metadata={"fallback": True, "note": "LobeHub server not reachable"},
        )

    def dispatch(self, brief: str, project_name: str | None = None) -> LobeHubResult:
        if not brief:
            return LobeHubResult(
                ok=False, brief="", command="", returncode=-1, stdout="",
                stderr="No brief provided", cwd="", status="failed",
            )
        if project_name is None:
            project_name = "".join(c if c.isalnum() else "_" for c in brief[:40]).strip("_") or "opa_project"
        project_dir = Path(os.path.join("data", "repos", "lobehub", "projects", project_name))

        # LobeHub has no stable public REST contract across versions; scaffold by
        # default and only POST when an explicit base URL is supplied.
        env_base = os.environ.get("LOBEHUB_BASE_URL")
        if not env_base:
            return self._simulate(project_dir, brief)

        try:
            import httpx

            resp = httpx.post(
                f"{env_base}/agent-teams",
                json=self._build_manifest(brief),
                timeout=self.timeout,
            )
            if resp.status_code < 300:
                return LobeHubResult(
                    ok=True, brief=brief, command=f"POST {env_base}/agent-teams",
                    returncode=0, stdout=resp.text[:8000], stderr="", cwd=str(project_dir),
                    manifest_path="", status="success",
                    metadata={"fallback": False, "http_status": resp.status_code},
                )
            return LobeHubResult(
                ok=False, brief=brief, command=f"POST {env_base}/agent-teams",
                returncode=resp.status_code, stdout=resp.text[:8000],
                stderr=resp.text[:4000], cwd=str(project_dir), status="error",
                metadata={"fallback": False},
            )
        except Exception as exc:  # noqa: BLE001
            simulated = self._simulate(project_dir, brief)
            simulated.metadata["original_error"] = str(exc)[:500]
            return simulated

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        self._check_network_policy(node)
        brief = payload.get("brief") or payload.get("intent") or ""
        result = self.dispatch(brief=brief, project_name=payload.get("project_name"))
        return result.metadata | {
            "module": node.name,
            "status": result.status,
            "brief": result.brief,
            "manifest_path": result.manifest_path,
            "command": result.command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": result.cwd,
        }


def _make_lobehub(config, network_policy, audit_logger, task):
    adapter = LobeHubAdapter(
        base_url=os.environ.get("LOBEHUB_BASE_URL", DEFAULT_LOBEHUB_BASE),
        network_policy=network_policy,
        audit_logger=audit_logger,
    )
    payload = dict(task.payload)
    payload.setdefault("brief", task.intent)
    return adapter, payload
