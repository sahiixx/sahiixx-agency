"""n8n automation adapter.

Connects the promoted ``n8n`` ecosystem module to the execution pipeline. n8n is
a fair-code workflow automation platform with a REST API. The adapter creates /
triggers a workflow via the local n8n API when reachable (base URL + API key in
payload/env), otherwise scaffolds a workflow JSON so the dispatch chain stays
green offline.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy

DEFAULT_N8N_BASE = "http://localhost:5678/api/v1"


@dataclass
class N8nResult:
    ok: bool
    brief: str
    command: str
    returncode: int
    stdout: str
    stderr: str
    cwd: str
    workflow_path: str = ""
    status: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.status:
            self.status = "success" if self.ok else "failed"


class N8nAdapter:
    """Adapter that scaffolds / triggers an n8n workflow from a brief."""

    def __init__(
        self,
        base_url: str = DEFAULT_N8N_BASE,
        api_key: str | None = None,
        network_policy: NetworkPolicy | None = None,
        audit_logger: AuditLogger | None = None,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
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
                    "N8nAdapter",
                    node.id,
                    {"blocked_hosts": blocked, "allowlist": sorted(policy.allowlist)},
                )
            raise RuntimeError(message)

    def _build_workflow(self, brief: str) -> dict[str, Any]:
        safe = "".join(c if c.isalnum() else " " for c in brief[:40]).strip()
        return {
            "name": f"OPA: {safe}",
            "nodes": [
                {
                    "parameters": {},
                    "name": "Manual Trigger",
                    "type": "n8n-nodes-base.manualTrigger",
                    "typeVersion": 1,
                    "position": [250, 300],
                },
                {
                    "parameters": {"content": brief},
                    "name": "Set Brief",
                    "type": "n8n-nodes-base.set",
                    "typeVersion": 3,
                    "position": [500, 300],
                },
            ],
            "connections": {
                "Manual Trigger": {"main": [[{"node": "Set Brief", "type": "main", "index": 0}]]}
            },
            "settings": {"executionOrder": "v1"},
            "active": False,
        }

    def _write_workflow(self, project_dir: Path, brief: str) -> Path:
        project_dir.mkdir(parents=True, exist_ok=True)
        path = project_dir / "workflow.json"
        path.write_text(json.dumps(self._build_workflow(brief), indent=2), encoding="utf-8")
        return path

    def _simulate(self, project_dir: Path, brief: str) -> N8nResult:
        path = self._write_workflow(project_dir, brief)
        return N8nResult(
            ok=True,
            brief=brief,
            command="POST /workflows <simulated>",
            returncode=0,
            stdout=(
                f"[SIMULATED] n8n workflow scaffolded at {path}\n"
                f"next_step: import into n8n (http://localhost:5678) or POST to "
                f"{self.base_url}/workflows with header X-N8N-API-KEY\n"
            ),
            stderr="",
            cwd=str(project_dir),
            workflow_path=str(path),
            status="simulated",
            metadata={"fallback": True, "note": "n8n API not reachable"},
        )

    def dispatch(self, brief: str, project_name: str | None = None) -> N8nResult:
        if not brief:
            return N8nResult(
                ok=False, brief="", command="", returncode=-1, stdout="",
                stderr="No brief provided", cwd="", status="failed",
            )
        if project_name is None:
            project_name = "".join(c if c.isalnum() else "_" for c in brief[:40]).strip("_") or "opa_project"
        project_dir = Path(os.path.join("data", "repos", "n8n", "projects", project_name))

        if not self.api_key:
            return self._simulate(project_dir, brief)

        try:
            import httpx

            resp = httpx.post(
                f"{self.base_url}/workflows",
                json=self._build_workflow(brief),
                headers={"X-N8N-API-KEY": self.api_key},
                timeout=self.timeout,
            )
            if resp.status_code < 300:
                return N8nResult(
                    ok=True, brief=brief, command=f"POST {self.base_url}/workflows",
                    returncode=0, stdout=resp.text[:8000], stderr="", cwd=str(project_dir),
                    workflow_path="", status="success",
                    metadata={"fallback": False, "http_status": resp.status_code},
                )
            return N8nResult(
                ok=False, brief=brief, command=f"POST {self.base_url}/workflows",
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
            "workflow_path": result.workflow_path,
            "command": result.command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": result.cwd,
        }


def _make_n8n(config, network_policy, audit_logger, task):
    adapter = N8nAdapter(
        base_url=os.environ.get("N8N_BASE_URL", DEFAULT_N8N_BASE),
        api_key=os.environ.get("N8N_API_KEY"),
        network_policy=network_policy,
        audit_logger=audit_logger,
    )
    payload = dict(task.payload)
    payload.setdefault("brief", task.intent)
    return adapter, payload
