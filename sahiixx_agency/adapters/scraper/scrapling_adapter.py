"""Scrapling adapter.

Connects the promoted ``scrapling`` ecosystem module (adaptive web scraping) to
the execution pipeline. Scaffolds a crawl script using the Scrapling library and
runs it when the package + interpreter are available, otherwise returns a
deterministic simulation so the dispatch chain stays green offline.
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

_SCRAPLING_TEMPLATE = '''\
"""OPA-scaffolded Scrapling crawl."""
from scrapling import Fetcher

async def main():
    url = "{url}"
    page = await Fetcher.get(url)
    print(page.css("title::text").get() if page else "no page")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
'''


@dataclass
class ScraplingResult:
    ok: bool
    brief: str
    url: str
    command: str
    returncode: int
    stdout: str
    stderr: str
    cwd: str
    scaffold_path: str = ""
    status: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.status:
            self.status = "success" if self.ok else "failed"


class ScraplingAdapter:
    """Adapter that scaffolds / runs a Scrapling crawl from a brief."""

    def __init__(
        self,
        repo_dir: str | Path | None = None,
        clone_base_dir: str | Path | None = None,
        python_executable: str = "python",
        timeout: int = 120,
        fallback_on_failure: bool = True,
        network_policy: NetworkPolicy | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        base = Path(clone_base_dir) if clone_base_dir else Path(DEFAULT_CLONE_BASE)
        self.repo_dir = Path(repo_dir) if repo_dir else base / "scrapling"
        self.python_executable = python_executable
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
                    "ScraplingAdapter",
                    node.id,
                    {"blocked_hosts": blocked, "allowlist": sorted(policy.allowlist)},
                )
            raise RuntimeError(message)

    def _write_scaffold(self, project_dir: Path, url: str) -> Path:
        project_dir.mkdir(parents=True, exist_ok=True)
        scaffold = project_dir / "crawl.py"
        scaffold.write_text(_SCRAPLING_TEMPLATE.replace("{url}", url), encoding="utf-8")
        return scaffold

    def _run_subprocess(self, project_dir: Path, command: list[str]) -> ScraplingResult:
        command_str = " ".join(command)
        try:
            proc = subprocess.run(
                command,
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            return ScraplingResult(
                ok=proc.returncode == 0,
                brief="",
                url="",
                command=command_str,
                returncode=proc.returncode,
                stdout=proc.stdout[:8000] if proc.stdout else "",
                stderr=proc.stderr[:4000] if proc.stderr else "",
                cwd=str(self.repo_dir),
                scaffold_path=str(project_dir / "crawl.py"),
                status="success" if proc.returncode == 0 else "error",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except subprocess.TimeoutExpired as exc:
            return ScraplingResult(
                ok=False, brief="", url="", command=command_str, returncode=-1,
                stdout=str(exc.stdout or ""), stderr=f"Timeout after {self.timeout}s",
                cwd=str(self.repo_dir), scaffold_path=str(project_dir / "crawl.py"),
                status="timeout", metadata={"timeout": self.timeout, "fallback": False},
            )
        except Exception as exc:  # noqa: BLE001
            return ScraplingResult(
                ok=False, brief="", url="", command=command_str, returncode=-1,
                stdout="", stderr=str(exc), cwd=str(self.repo_dir),
                scaffold_path=str(project_dir / "crawl.py"),
                status="exception", metadata={"timeout": self.timeout, "fallback": False},
            )

    def _simulate(self, project_dir: Path, brief: str, url: str) -> ScraplingResult:
        scaffold = self._write_scaffold(project_dir, url)
        return ScraplingResult(
            ok=True,
            brief=brief,
            url=url,
            command=f"{self.python_executable} crawl.py <simulated>",
            returncode=0,
            stdout=(
                f"[SIMULATED] Scrapling crawl scaffolded at {scaffold}\n"
                f"target: {url}\n"
                f"next_step: pip install scrapling && cd {project_dir} && "
                f"{self.python_executable} crawl.py\n"
            ),
            stderr="",
            cwd=str(self.repo_dir),
            scaffold_path=str(scaffold),
            status="simulated",
            metadata={"timeout": self.timeout, "fallback": True, "note": "Scrapling not executed"},
        )

    def dispatch(self, brief: str, url: str | None = None, project_name: str | None = None) -> ScraplingResult:
        if not brief:
            return ScraplingResult(
                ok=False, brief="", url="", command="", returncode=-1, stdout="",
                stderr="No brief provided", cwd="", status="failed",
            )
        target = url or _extract_url(brief)
        if project_name is None:
            project_name = "".join(c if c.isalnum() else "_" for c in brief[:40]).strip("_") or "opa_project"
        project_dir = self.repo_dir / "projects" / project_name

        if not self.repo_dir.exists():
            return self._simulate(project_dir, brief, target)

        scaffold = self._write_scaffold(project_dir, target)
        result = self._run_subprocess(project_dir, [self.python_executable, str(scaffold)])
        if not result.ok and self.fallback_on_failure:
            simulated = self._simulate(project_dir, brief, target)
            simulated.metadata["original_error"] = result.stderr[:500]
            return simulated
        return result

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        self._check_network_policy(node)
        brief = payload.get("brief") or payload.get("intent") or ""
        result = self.dispatch(brief=brief, url=payload.get("url"), project_name=payload.get("project_name"))
        return result.metadata | {
            "module": node.name,
            "status": result.status,
            "brief": result.brief,
            "url": result.url,
            "scaffold_path": result.scaffold_path,
            "command": result.command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": result.cwd,
        }


def _extract_url(text: str) -> str:
    import re

    match = re.search(r"https?://[^\s]+", text)
    return match.group(0) if match else "https://example.com"


def _make_scrapling(config, network_policy, audit_logger, task):
    from sahiixx_agency.adapters.scraper.scrapling_adapter import ScraplingAdapter

    adapter = ScraplingAdapter(
        clone_base_dir=os.path.join(config.data_dir, "repos"),
        network_policy=network_policy,
        audit_logger=audit_logger,
    )
    payload = dict(task.payload)
    payload.setdefault("brief", task.intent)
    return adapter, payload
