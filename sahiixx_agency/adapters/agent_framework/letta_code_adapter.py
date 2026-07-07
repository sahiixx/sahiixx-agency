"""Letta Code adapter that dispatches stateful agent prompts to the cloned repo.

Runs the ``letta-ai/letta-code`` CLI harness from ``data/repos/letta-code``.
Since Letta Code is an agentic stateful agent harness (not a single fixed
entrypoint), the adapter translates an OPA payload into a project brief and
tries to start the local agent CLI, falling back to a deterministic simulation
when the repo or binary is unavailable.
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

DEFAULT_LETTA_CODE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "repos", "letta-code")
)


@dataclass
class LettaCodeResult:
    """Result of dispatching a stateful agent brief to Letta Code."""

    ok: bool
    brief: str
    persona: str
    command: str
    returncode: int
    stdout: str
    stderr: str
    cwd: str
    project_dir: str
    status: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.status:
            self.status = "success" if self.ok else "failed"


class LettaCodeAdapter:
    """Adapter that dispatches a stateful agent brief to the local Letta Code repo."""

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
                Path(clone_base_dir) / "letta-code"
                if clone_base_dir
                else DEFAULT_LETTA_CODE_DIR
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
                    "LettaCodeAdapter",
                    node.id,
                    {"blocked_hosts": blocked, "allowlist": sorted(policy.allowlist)},
                )
            raise RuntimeError(message)

    PERSONAS: tuple[str, ...] = (
        "tutorial",
        "coder",
        "researcher",
        "writer",
        "default",
    )

    def _infer_persona(self, brief: str) -> str:
        brief_lower = brief.lower()
        persona_keywords = {
            "coder": ["code", "coding", "debug", "program", "api", "refactor"],
            "researcher": ["research", "investigate", "analyze", "paper", "study"],
            "writer": ["write", "draft", "blog", "copy", "story", "article"],
            "tutorial": ["tutorial", "learn", "how to", "guide", "walkthrough"],
        }
        for persona, keywords in persona_keywords.items():
            if any(kw in brief_lower for kw in keywords):
                return persona
        return "default"

    def _write_brief(self, project_dir: Path, brief: str, persona: str) -> None:
        """Create a minimal Letta Code project brief."""
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "brief.txt").write_text(brief, encoding="utf-8")
        (project_dir / "persona.txt").write_text(persona, encoding="utf-8")

    def _find_bun(self) -> list[str]:
        """Return the command list to invoke bun."""
        import shutil

        bun = shutil.which("bun")
        if bun:
            return [bun]
        return ["npx", "bun"]

    def _build_command(self, project_dir: Path, persona: str, one_shot: str | None = None) -> list[str]:
        """Build the command to start the Letta Code agent CLI.

        Letta Code is primarily driven by an interactive local CLI. We try to
        start the agent in a non-interactive way using ``bun run letta`` or
        ``npx letta`` with the configured persona and brief directory.
        """
        if (self.repo_dir / "letta.js").exists() or (self.repo_dir / "package.json").exists():
            cmd = [*self._find_bun(), "run", "letta", "--new-agent", "--personality", persona]
            if one_shot:
                cmd.extend(["-p", one_shot])
            return cmd
        return [
            "python",
            "-c",
            (
                f"import sys; "
                f"print('Letta Code project initialized at {project_dir} for persona {persona}'); "
                f"sys.exit(0)"
            ),
        ]

    def _run_subprocess(self, project_dir: Path, command: list[str]) -> LettaCodeResult:
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
            return LettaCodeResult(
                ok=proc.returncode == 0,
                brief="",
                persona="",
                command=command_str,
                returncode=proc.returncode,
                stdout=proc.stdout[:8000] if proc.stdout else "",
                stderr=proc.stderr[:4000] if proc.stderr else "",
                cwd=str(self.repo_dir),
                project_dir=str(project_dir),
                status="success" if proc.returncode == 0 else "error",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except subprocess.TimeoutExpired as exc:
            return LettaCodeResult(
                ok=False,
                brief="",
                persona="",
                command=command_str,
                returncode=-1,
                stdout=str(exc.stdout or ""),
                stderr=f"Timeout after {self.timeout}s",
                cwd=str(self.repo_dir),
                project_dir=str(project_dir),
                status="timeout",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except Exception as exc:  # noqa: BLE001
            return LettaCodeResult(
                ok=False,
                brief="",
                persona="",
                command=command_str,
                returncode=-1,
                stdout="",
                stderr=str(exc),
                cwd=str(self.repo_dir),
                project_dir=str(project_dir),
                status="exception",
                metadata={"timeout": self.timeout, "fallback": False},
            )

    def _simulate(self, project_dir: Path, brief: str, persona: str) -> LettaCodeResult:
        """Simulated fallback that returns a deterministic Letta Code-like plan."""
        return LettaCodeResult(
            ok=True,
            brief=brief,
            persona=persona,
            command="bun run letta --new-agent --personality <persona> <simulated>",
            returncode=0,
            stdout=(
                f"[SIMULATED] Letta Code stateful agent plan\n"
                f"persona: {persona}\n"
                f"project: {project_dir}\n"
                f"memory: persistent long-term memory blocks enabled\n"
                f"next_step: run 'letta' in {project_dir} and chat with the agent\n"
            ),
            stderr="",
            cwd=str(self.repo_dir),
            project_dir=str(project_dir),
            status="simulated",
            metadata={"timeout": self.timeout, "fallback": True, "note": "Letta Code repo unavailable"},
        )

    def dispatch(
        self,
        brief: str,
        persona: str | None = None,
        project_name: str | None = None,
        simulate: bool = False,
    ) -> LettaCodeResult:
        """Dispatch a stateful agent brief to Letta Code.

        Args:
            brief: Plain-language description of the agent to spin up.
            persona: Optional persona (e.g. tutorial, coder, researcher, writer).
            project_name: Optional project directory name.
            simulate: If True, skip the real subprocess and return a simulation.

        Returns:
            LettaCodeResult with stdout, stderr, returncode, and status.
        """
        if persona is None:
            persona = self._infer_persona(brief)
        if project_name is None:
            project_name = "".join(c if c.isalnum() else "_" for c in brief[:40]).strip("_")
            if not project_name:
                project_name = "opa_project"
        project_dir = Path(self.repo_dir) / "projects" / project_name
        self._write_brief(project_dir, brief, persona)

        if simulate or not self.repo_dir.exists():
            return self._simulate(project_dir, brief, persona)

        # Prefer a quick non-interactive agent invocation if deps are installed.
        command = self._build_command(project_dir, persona, one_shot=brief[:200])
        result = self._run_subprocess(project_dir, command)
        if not result.ok and self.fallback_on_failure:
            simulated = self._simulate(project_dir, brief, persona)
            simulated.metadata["original_error"] = result.stderr[:500]
            simulated.metadata["original_status"] = result.status
            return simulated
        return result

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        """Conform to the agency adapter interface: run from RepoNode + payload."""
        import asyncio

        # Enforce egress policy before any outbound/repo work.
        self._check_network_policy(node)

        brief = payload.get("brief") or payload.get("intent") or ""
        persona = payload.get("persona")
        project_name = payload.get("project_name")
        if not brief:
            return {
                "module": node.name,
                "status": "failed",
                "error": "No brief provided in payload",
            }
        result = await asyncio.to_thread(
            self.dispatch,
            brief=brief,
            persona=persona,
            project_name=project_name,
            simulate=payload.get("simulate", False),
        )
        return result.metadata | {
            "module": node.name,
            "status": result.status,
            "brief": result.brief,
            "persona": result.persona,
            "project_dir": result.project_dir,
            "command": result.command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": result.cwd,
        }


def run_letta_code(
    brief: str,
    persona: str | None = None,
    repo_dir: str | Path = DEFAULT_LETTA_CODE_DIR,
) -> LettaCodeResult:
    """Convenience function: dispatch a single brief to Letta Code."""
    adapter = LettaCodeAdapter(repo_dir=repo_dir)
    return adapter.dispatch(brief, persona=persona)


def _demo() -> None:
    """Exercise the adapter against simulated and real targets."""
    test_brief = "Spin up a stateful agent with long-term memory that tracks my research notes."

    print("=== Letta Code Adapter Test Harness ===")
    print(f"Repo dir: {DEFAULT_LETTA_CODE_DIR}")
    print()

    # 1. Simulate mode
    sim_adapter = LettaCodeAdapter(fallback_on_failure=False)
    sim_result = sim_adapter.dispatch(test_brief, simulate=True)
    print("--- Simulation ---")
    print(f"status={sim_result.status} ok={sim_result.ok}")
    print(f"stdout={sim_result.stdout[:500]}")
    print()

    # 2. Real attempt (fallback to simulation if not available)
    real_adapter = LettaCodeAdapter(fallback_on_failure=True)
    real_result = real_adapter.dispatch(test_brief)
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
        id="letta-code",
        name="letta-code",
        owner="letta-ai",
        full_name="letta-ai/letta-code",
        url="https://github.com/letta-ai/letta-code",
    )
    payload = {
        "brief": test_brief,
        "persona": "researcher",
        "simulate": True,
    }
    result = asyncio.run(real_adapter.run(node, payload))
    print("--- Async interface ---")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    _demo()
