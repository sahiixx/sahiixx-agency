"""Career-Ops adapter that dispatches job posting URLs to the cloned repo.

Runs ``cops oferta <url>`` inside ``data/repos/career-ops`` (or whatever
``repo_dir`` is configured).  Includes subprocess runner, timeout, environment
injection, output capture, and a fallback simulation mode.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy

DEFAULT_CAREER_OPS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "repos", "career-ops")
)


@dataclass
class CareerOpsResult:
    """Result of dispatching a URL to Career-Ops."""

    ok: bool
    url: str
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


class CareerOpsAdapter:
    """Adapter that dispatches ``cops oferta <url>`` to the local career-ops repo."""

    def __init__(
        self,
        repo_dir: str | Path | None = None,
        clone_base_dir: str | Path | None = None,
        timeout: int = 300,
        fallback_on_failure: bool = True,
        env: dict[str, str] | None = None,
        network_policy: NetworkPolicy | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        if repo_dir is None:
            repo_dir = (
                Path(clone_base_dir) / "career-ops"
                if clone_base_dir
                else DEFAULT_CAREER_OPS_DIR
            )
        self.repo_dir = Path(repo_dir)
        self.timeout = timeout
        self.fallback_on_failure = fallback_on_failure
        self.env = env or {}
        self.network_policy = network_policy
        self.audit_logger = audit_logger

    def _check_network_policy(self, node: RepoNode) -> None:
        """Verify declared external hosts against the egress policy."""
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
                    "CareerOpsAdapter",
                    node.id,
                    {"blocked_hosts": blocked, "allowlist": sorted(policy.allowlist)},
                )
            raise RuntimeError(message)

    @property
    def cops_executable(self) -> Path:
        return self.repo_dir / "cops"

    def _build_command(self, url: str, extra_args: list[str] | None = None) -> list[str]:
        cmd = [str(self.cops_executable), "oferta", url]
        if extra_args:
            cmd.extend(extra_args)
        return cmd

    def _run_subprocess(self, url: str, extra_args: list[str] | None = None) -> CareerOpsResult:
        command = self._build_command(url, extra_args)
        command_str = " ".join(shlex.quote(str(c)) for c in command)

        run_env = {**os.environ, **self.env}

        try:
            proc = subprocess.run(
                command,
                cwd=str(self.repo_dir),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=run_env,
                check=False,
            )
            return CareerOpsResult(
                ok=proc.returncode == 0,
                url=url,
                command=command_str,
                returncode=proc.returncode,
                stdout=proc.stdout[:8000] if proc.stdout else "",
                stderr=proc.stderr[:4000] if proc.stderr else "",
                cwd=str(self.repo_dir),
                status="success" if proc.returncode == 0 else "error",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except subprocess.TimeoutExpired as exc:
            return CareerOpsResult(
                ok=False,
                url=url,
                command=command_str,
                returncode=-1,
                stdout=str(exc.stdout or ""),
                stderr=f"Timeout after {self.timeout}s",
                cwd=str(self.repo_dir),
                status="timeout",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except Exception as exc:  # noqa: BLE001
            return CareerOpsResult(
                ok=False,
                url=url,
                command=command_str,
                returncode=-1,
                stdout="",
                stderr=str(exc),
                cwd=str(self.repo_dir),
                status="exception",
                metadata={"timeout": self.timeout, "fallback": False},
            )

    def _simulate(self, url: str) -> CareerOpsResult:
        """Simulated fallback that returns a deterministic Career-Ops-like result."""
        return CareerOpsResult(
            ok=True,
            url=url,
            command="cops oferta <simulated>",
            returncode=0,
            stdout=(
                f"[SIMULATED] Career-Ops evaluation for {url}\n"
                "score: 72/100\n"
                "tier: B\n"
                "recommendation: apply-with-customization\n"
                "archetype-fit: senior-engineering-manager\n"
                "location-policy: remote-friendly\n"
            ),
            stderr="",
            cwd=str(self.repo_dir),
            status="simulated",
            metadata={"timeout": self.timeout, "fallback": True, "note": "Career-Ops repo unavailable"},
        )

    def dispatch(
        self,
        url: str,
        extra_args: list[str] | None = None,
        simulate: bool = False,
    ) -> CareerOpsResult:
        """Dispatch a job posting URL to Career-Ops.

        Args:
            url: Job posting URL to evaluate.
            extra_args: Additional arguments passed after ``cops oferta <url>``.
            simulate: If True, skip the real subprocess and return a simulation.

        Returns:
            CareerOpsResult with stdout, stderr, returncode, and status.
        """
        if simulate or not self.cops_executable.exists():
            return self._simulate(url)

        result = self._run_subprocess(url, extra_args)
        if not result.ok and self.fallback_on_failure:
            simulated = self._simulate(url)
            simulated.metadata["original_error"] = result.stderr[:500]
            simulated.metadata["original_status"] = result.status
            return simulated
        return result

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        """Conform to the agency adapter interface: run from RepoNode + payload."""
        # Enforce egress policy before any outbound/repo work.
        self._check_network_policy(node)

        url = payload.get("url") or payload.get("intent", "")
        if not url:
            return {
                "module": node.name,
                "status": "failed",
                "error": "No URL provided in payload",
            }
        result = self.dispatch(url, extra_args=payload.get("extra_args"), simulate=payload.get("simulate", False))
        return result.metadata | {
            "module": node.name,
            "status": result.status,
            "url": result.url,
            "command": result.command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": result.cwd,
        }


def run_cops_oferta(url: str, repo_dir: str | Path = DEFAULT_CAREER_OPS_DIR) -> CareerOpsResult:
    """Convenience function: dispatch a single URL to Career-Ops."""
    adapter = CareerOpsAdapter(repo_dir=repo_dir)
    return adapter.dispatch(url)


def _demo() -> None:
    """Exercise the adapter against real and simulated targets."""
    test_url = "https://example.com/jobs/senior-engineer-ai"

    print("=== Career-Ops Adapter Test Harness ===")
    print(f"Repo dir: {DEFAULT_CAREER_OPS_DIR}")
    print()

    # 1. Simulate mode
    sim_adapter = CareerOpsAdapter(fallback_on_failure=False)
    sim_result = sim_adapter.dispatch(test_url, simulate=True)
    print("--- Simulation ---")
    print(f"status={sim_result.status} ok={sim_result.ok}")
    print(f"stdout={sim_result.stdout[:500]}")
    print()

    # 2. Real attempt (fallback to simulation if cops fails / not available)
    real_adapter = CareerOpsAdapter(fallback_on_failure=True)
    real_result = real_adapter.dispatch(test_url)
    print("--- Real dispatch (or fallback) ---")
    print(f"status={real_result.status} ok={real_result.ok}")
    print(f"command={real_result.command}")
    print(f"returncode={real_result.returncode}")
    print(f"stdout={real_result.stdout[:1000]}")
    if real_result.stderr:
        print(f"stderr={real_result.stderr[:500]}")
    print()

    # 3. Async interface demo
    import asyncio

    node = RepoNode(
        id="career-ops",
        name="career-ops",
        owner="sahiixx",
        full_name="sahiixx/career-ops",
        url="https://github.com/sahiixx/career-ops",
    )
    payload = {"url": test_url, "simulate": True}
    result = asyncio.run(real_adapter.run(node, payload))
    print("--- Async interface ---")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    _demo()
