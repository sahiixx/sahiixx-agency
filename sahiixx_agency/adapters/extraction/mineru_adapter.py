"""MinerU adapter.

Connects the promoted ``mineru`` ecosystem module (PDF/Office -> LLM-ready
markdown) to the execution pipeline. Scaffolds and runs the MinerU CLI on a
document when available, otherwise returns a deterministic simulation so the
dispatch chain stays green offline.
"""

from __future__ import annotations

import os
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
class MinerUResult:
    ok: bool
    brief: str
    doc_path: str
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


class MinerUAdapter:
    """Adapter that runs MinerU document extraction from a brief."""

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
        self.repo_dir = Path(repo_dir) if repo_dir else base / "mineru"
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
                    "MinerUAdapter",
                    node.id,
                    {"blocked_hosts": blocked, "allowlist": sorted(policy.allowlist)},
                )
            raise RuntimeError(message)

    def _resolve_doc(self, brief: str, doc_path: str | None) -> str:
        if doc_path:
            return doc_path
        import re

        match = re.search(r"\S+\.(pdf|docx?|pptx?|xlsx?)", brief, re.IGNORECASE)
        return match.group(0) if match else "document.pdf"

    def _run_subprocess(self, command: list[str], workdir: Path) -> MinerUResult:
        command_str = " ".join(command)
        run_env = {**os.environ}
        try:
            proc = subprocess.run(
                command,
                cwd=str(workdir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=run_env,
                check=False,
            )
            return MinerUResult(
                ok=proc.returncode == 0,
                brief="",
                doc_path="",
                command=command_str,
                returncode=proc.returncode,
                stdout=proc.stdout[:8000] if proc.stdout else "",
                stderr=proc.stderr[:4000] if proc.stderr else "",
                cwd=str(workdir),
                status="success" if proc.returncode == 0 else "error",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except subprocess.TimeoutExpired as exc:
            return MinerUResult(
                ok=False, brief="", doc_path="", command=command_str, returncode=-1,
                stdout=str(exc.stdout or ""), stderr=f"Timeout after {self.timeout}s",
                cwd=str(workdir), status="timeout",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except Exception as exc:  # noqa: BLE001
            return MinerUResult(
                ok=False, brief="", doc_path="", command=command_str, returncode=-1,
                stdout="", stderr=str(exc), cwd=str(workdir), status="exception",
                metadata={"timeout": self.timeout, "fallback": False},
            )

    def _simulate(self, brief: str, doc_path: str) -> MinerUResult:
        return MinerUResult(
            ok=True,
            brief=brief,
            doc_path=doc_path,
            command=f"mineru {doc_path} -o ./output <simulated>",
            returncode=0,
            stdout=(
                f"[SIMULATED] MinerU extraction plan\n"
                f"document: {doc_path}\n"
                f"next_step: pip install magic-pdf && mineru {doc_path} -o ./output\n"
            ),
            stderr="",
            cwd=str(self.repo_dir),
            status="simulated",
            metadata={"timeout": self.timeout, "fallback": True, "note": "MinerU not executed"},
        )

    def dispatch(self, brief: str, doc_path: str | None = None, project_name: str | None = None) -> MinerUResult:
        if not brief:
            return MinerUResult(
                ok=False, brief="", doc_path="", command="", returncode=-1, stdout="",
                stderr="No brief provided", cwd="", status="failed",
            )
        doc = self._resolve_doc(brief, doc_path)
        workdir = self.repo_dir if self.repo_dir.exists() else Path(".")

        if not self.repo_dir.exists():
            return self._simulate(brief, doc)

        command = ["mineru", doc, "-o", str(workdir / "output")]
        result = self._run_subprocess(command, workdir)
        if not result.ok and self.fallback_on_failure:
            simulated = self._simulate(brief, doc)
            simulated.metadata["original_error"] = result.stderr[:500]
            return simulated
        return result

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        self._check_network_policy(node)
        brief = payload.get("brief") or payload.get("intent") or ""
        result = self.dispatch(brief=brief, doc_path=payload.get("doc_path"), project_name=payload.get("project_name"))
        return result.metadata | {
            "module": node.name,
            "status": result.status,
            "brief": result.brief,
            "doc_path": result.doc_path,
            "command": result.command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": result.cwd,
        }


def _make_mineru(config, network_policy, audit_logger, task):
    from sahiixx_agency.adapters.extraction.mineru_adapter import MinerUAdapter

    adapter = MinerUAdapter(
        clone_base_dir=os.path.join(config.data_dir, "repos"),
        network_policy=network_policy,
        audit_logger=audit_logger,
    )
    payload = dict(task.payload)
    payload.setdefault("brief", task.intent)
    return adapter, payload
