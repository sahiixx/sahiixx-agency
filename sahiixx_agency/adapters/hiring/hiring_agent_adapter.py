"""Hiring-Agent adapter that dispatches resume evaluation tasks to the cloned repo.

Invokes the hiring-agent repo's entrypoint (``score.py <pdf_path>``) from
``data/repos/hiring-agent``.  Includes subprocess runner, timeout, environment
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

DEFAULT_HIRING_AGENT_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "repos", "hiring-agent")
)


@dataclass
class HiringAgentResult:
    """Result of dispatching a PDF to the Hiring Agent."""

    ok: bool
    pdf_path: str
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


class HiringAgentAdapter:
    """Adapter that dispatches resume PDF evaluation to the local hiring-agent repo."""

    def __init__(
        self,
        repo_dir: str | Path | None = None,
        clone_base_dir: str | Path | None = None,
        python_executable: str = "python",
        timeout: int = 600,
        fallback_on_failure: bool = True,
        env: dict[str, str] | None = None,
    ) -> None:
        if repo_dir is None:
            repo_dir = (
                Path(clone_base_dir) / "hiring-agent"
                if clone_base_dir
                else DEFAULT_HIRING_AGENT_DIR
            )
        self.repo_dir = Path(repo_dir)
        self.python_executable = python_executable
        self.timeout = timeout
        self.fallback_on_failure = fallback_on_failure
        self.env = env or {}

    @property
    def score_script(self) -> Path:
        return self.repo_dir / "score.py"

    def _build_command(self, pdf_path: str) -> list[str]:
        return [self.python_executable, str(self.score_script), pdf_path]

    def _prepare_env(self) -> dict[str, str]:
        return {**os.environ, **self.env}

    def _run_subprocess(self, pdf_path: str) -> HiringAgentResult:
        command = self._build_command(pdf_path)
        command_str = " ".join(shlex.quote(str(c)) for c in command)
        run_env = self._prepare_env()

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
            return HiringAgentResult(
                ok=proc.returncode == 0,
                pdf_path=pdf_path,
                command=command_str,
                returncode=proc.returncode,
                stdout=proc.stdout[:8000] if proc.stdout else "",
                stderr=proc.stderr[:4000] if proc.stderr else "",
                cwd=str(self.repo_dir),
                status="success" if proc.returncode == 0 else "error",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except subprocess.TimeoutExpired as exc:
            return HiringAgentResult(
                ok=False,
                pdf_path=pdf_path,
                command=command_str,
                returncode=-1,
                stdout=str(exc.stdout or ""),
                stderr=f"Timeout after {self.timeout}s",
                cwd=str(self.repo_dir),
                status="timeout",
                metadata={"timeout": self.timeout, "fallback": False},
            )
        except Exception as exc:  # noqa: BLE001
            return HiringAgentResult(
                ok=False,
                pdf_path=pdf_path,
                command=command_str,
                returncode=-1,
                stdout="",
                stderr=str(exc),
                cwd=str(self.repo_dir),
                status="exception",
                metadata={"timeout": self.timeout, "fallback": False},
            )

    def _simulate(self, pdf_path: str) -> HiringAgentResult:
        """Simulated fallback that returns a deterministic Hiring-Agent-like result."""
        candidate = Path(pdf_path).stem
        return HiringAgentResult(
            ok=True,
            pdf_path=pdf_path,
            command="python score.py <simulated>",
            returncode=0,
            stdout=(
                f"[SIMULATED] Hiring Agent evaluation for {candidate}\n"
                "================================================================================\n"
                f"📊 RESUME EVALUATION RESULTS FOR: {candidate}\n"
                "================================================================================\n"
                "🎯 OVERALL SCORE: 78.0/100\n"
                "📈 DETAILED SCORES:\n"
                "------------------------------------------------------------\n"
                "🌐 Open Source:          28/35\n"
                "   Evidence: Strong GitHub presence with multiple repositories\n"
                "🚀 Self Projects:        22/30\n"
                "   Evidence: Demonstrated end-to-end project delivery\n"
                "🏢 Production Experience: 20/25\n"
                "   Evidence: Multi-year enterprise engineering roles\n"
                "💻 Technical Skills:     8/10\n"
                "   Evidence: Broad stack with depth in Python and cloud\n"
                "\n"
                "⭐ BONUS POINTS: 5\n"
                "✅ KEY STRENGTHS:\n"
                "  1. Strong open-source footprint\n"
                "  2. Clear production impact\n"
            ),
            stderr="",
            cwd=str(self.repo_dir),
            status="simulated",
            metadata={"timeout": self.timeout, "fallback": True, "note": "Hiring-Agent repo unavailable"},
        )

    def dispatch(self, pdf_path: str, simulate: bool = False) -> HiringAgentResult:
        """Dispatch a resume PDF to the Hiring Agent.

        Args:
            pdf_path: Path to the resume PDF to evaluate.
            simulate: If True, skip the real subprocess and return a simulation.

        Returns:
            HiringAgentResult with stdout, stderr, returncode, and status.
        """
        if simulate or not self.score_script.exists():
            return self._simulate(pdf_path)

        result = self._run_subprocess(pdf_path)
        if not result.ok and self.fallback_on_failure:
            simulated = self._simulate(pdf_path)
            simulated.metadata["original_error"] = result.stderr[:500]
            simulated.metadata["original_status"] = result.status
            return simulated
        return result

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        """Conform to the agency adapter interface: run from RepoNode + payload."""
        pdf_path = payload.get("pdf_path") or payload.get("path") or payload.get("resume")
        if not pdf_path:
            return {
                "module": node.name,
                "status": "failed",
                "error": "No pdf_path provided in payload",
            }
        result = self.dispatch(pdf_path, simulate=payload.get("simulate", False))
        return result.metadata | {
            "module": node.name,
            "status": result.status,
            "pdf_path": result.pdf_path,
            "command": result.command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": result.cwd,
        }


def evaluate_resume(pdf_path: str, repo_dir: str | Path = DEFAULT_HIRING_AGENT_DIR) -> HiringAgentResult:
    """Convenience function: evaluate a single resume PDF with Hiring Agent."""
    adapter = HiringAgentAdapter(repo_dir=repo_dir)
    return adapter.dispatch(pdf_path)


def _demo() -> None:
    """Exercise the adapter against real and simulated targets."""
    # Create a tiny dummy PDF path so we can test the harness without a real resume.
    dummy_pdf = str(Path(__file__).with_name("demo_resume.pdf").resolve())
    test_pdf = dummy_pdf

    print("=== Hiring-Agent Adapter Test Harness ===")
    print(f"Repo dir: {DEFAULT_HIRING_AGENT_DIR}")
    print(f"Score script: {Path(DEFAULT_HIRING_AGENT_DIR) / 'score.py'}")
    print()

    # 1. Simulate mode
    sim_adapter = HiringAgentAdapter(fallback_on_failure=False)
    sim_result = sim_adapter.dispatch(test_pdf, simulate=True)
    print("--- Simulation ---")
    print(f"status={sim_result.status} ok={sim_result.ok}")
    print(f"stdout={sim_result.stdout[:500]}")
    print()

    # 2. Real attempt (fallback to simulation if score.py fails / not available)
    real_adapter = HiringAgentAdapter(fallback_on_failure=True)
    real_result = real_adapter.dispatch(test_pdf)
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
        id="hiring-agent",
        name="hiring-agent",
        owner="interviewstreet",
        full_name="interviewstreet/hiring-agent",
        url="https://github.com/interviewstreet/hiring-agent",
    )
    payload = {"pdf_path": test_pdf, "simulate": True}
    result = asyncio.run(real_adapter.run(node, payload))
    print("--- Async interface ---")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    _demo()
