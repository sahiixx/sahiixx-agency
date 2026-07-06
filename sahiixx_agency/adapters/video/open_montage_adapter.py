"""OpenMontage adapter that dispatches video production prompts to the cloned repo.

Runs the OpenMontage agentic video pipeline from ``data/repos/open-montage``.
Because OpenMontage is driven by an AI coding assistant reading YAML manifests and
Markdown skills, the adapter translates an OPA payload into the project structure
expected by OpenMontage: a project directory, a brief, and a pipeline selector.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sahiixx_agency.core.models import RepoNode

DEFAULT_OPEN_MONTAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "repos", "open-montage")
)


@dataclass
class OpenMontageResult:
    """Result of dispatching a video production brief to OpenMontage."""

    ok: bool
    brief: str
    pipeline: str
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


class OpenMontageAdapter:
    """Adapter that dispatches a video brief to the local OpenMontage repo."""

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
                Path(clone_base_dir) / "open-montage"
                if clone_base_dir
                else DEFAULT_OPEN_MONTAGE_DIR
            )
        self.repo_dir = Path(repo_dir)
        self.python_executable = python_executable
        self.timeout = timeout
        self.fallback_on_failure = fallback_on_failure
        self.env = env or {}

    @property
    def setup_marker(self) -> Path:
        """A cheap marker to tell whether ``make setup`` has been run."""
        return self.repo_dir / "tools" / "__init__.py"

    def _write_brief(self, project_dir: Path, brief: str, pipeline: str) -> None:
        """Create a minimal OpenMontage project brief."""
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "brief.txt").write_text(brief, encoding="utf-8")
        (project_dir / "pipeline.txt").write_text(pipeline, encoding="utf-8")

    def _build_command(self, project_dir: Path, pipeline: str) -> list[str]:
        """Build the command to start the OpenMontage pipeline.

        OpenMontage is orchestrated by the AI coding assistant, not a single
        CLI entrypoint. We provide a small runner script that loads the selected
        pipeline manifest and the brief so the agent can continue the work.
        """
        runner = self.repo_dir / "lib" / "opa_bridge.py"
        if runner.exists():
            return [self.python_executable, str(runner), str(project_dir), pipeline]
        # If the bridge doesn't exist yet, fall back to a simple scaffold command.
        return [
            self.python_executable,
            "-c",
            (
                f"import sys; "
                f"print('OpenMontage project initialized at {project_dir} for pipeline {pipeline}'); "
                f"sys.exit(0)"
            ),
        ]

    def _run_subprocess(self, project_dir: Path, command: list[str]) -> OpenMontageResult:
        command_str = " ".join(command)
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
            return OpenMontageResult(
                ok=proc.returncode == 0,
                brief="",
                pipeline="",
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
            return OpenMontageResult(
                ok=False,
                brief="",
                pipeline="",
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
            return OpenMontageResult(
                ok=False,
                brief="",
                pipeline="",
                command=command_str,
                returncode=-1,
                stdout="",
                stderr=str(exc),
                cwd=str(self.repo_dir),
                project_dir=str(project_dir),
                status="exception",
                metadata={"timeout": self.timeout, "fallback": False},
            )

    def _simulate(self, project_dir: Path, brief: str, pipeline: str) -> OpenMontageResult:
        """Simulated fallback that returns a deterministic OpenMontage-like plan."""
        return OpenMontageResult(
            ok=True,
            brief=brief,
            pipeline=pipeline,
            command="opa_bridge.py <simulated>",
            returncode=0,
            stdout=(
                f"[SIMULATED] OpenMontage production plan\n"
                f"pipeline: {pipeline}\n"
                f"project: {project_dir}\n"
                f"stages: research -> proposal -> script -> scene_plan -> assets -> edit -> compose\n"
                f"estimated_cost: $0.15 - $1.50\n"
                f"next_step: open {project_dir} in Claude Code / Cursor and run the pipeline\n"
            ),
            stderr="",
            cwd=str(self.repo_dir),
            project_dir=str(project_dir),
            status="simulated",
            metadata={"timeout": self.timeout, "fallback": True, "note": "OpenMontage repo unavailable"},
        )

    def dispatch(
        self,
        brief: str,
        pipeline: str = "animated_explainer",
        project_name: str | None = None,
        simulate: bool = False,
    ) -> OpenMontageResult:
        """Dispatch a video production brief to OpenMontage.

        Args:
            brief: Plain-language description of the video to produce.
            pipeline: One of the OpenMontage pipeline names (e.g. animated_explainer,
                cinematic, documentary_montage, talking_head, clip_factory).
            project_name: Optional project directory name. Defaults to a sanitized brief.
            simulate: If True, skip the real subprocess and return a simulation.

        Returns:
            OpenMontageResult with stdout, stderr, returncode, and status.
        """
        if project_name is None:
            project_name = "".join(c if c.isalnum() else "_" for c in brief[:40]).strip("_")
            if not project_name:
                project_name = "opa_project"
        project_dir = Path(self.repo_dir) / "projects" / project_name
        self._write_brief(project_dir, brief, pipeline)

        if simulate or not self.repo_dir.exists():
            return self._simulate(project_dir, brief, pipeline)

        command = self._build_command(project_dir, pipeline)
        result = self._run_subprocess(project_dir, command)
        if not result.ok and self.fallback_on_failure:
            simulated = self._simulate(project_dir, brief, pipeline)
            simulated.metadata["original_error"] = result.stderr[:500]
            simulated.metadata["original_status"] = result.status
            return simulated
        return result

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        """Conform to the agency adapter interface: run from RepoNode + payload."""
        brief = payload.get("brief") or payload.get("intent") or ""
        pipeline = payload.get("pipeline", "animated_explainer")
        project_name = payload.get("project_name")
        if not brief:
            return {
                "module": node.name,
                "status": "failed",
                "error": "No brief provided in payload",
            }
        result = self.dispatch(
            brief=brief,
            pipeline=pipeline,
            project_name=project_name,
            simulate=payload.get("simulate", False),
        )
        return result.metadata | {
            "module": node.name,
            "status": result.status,
            "brief": result.brief,
            "pipeline": result.pipeline,
            "project_dir": result.project_dir,
            "command": result.command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": result.cwd,
        }


def run_open_montage(
    brief: str,
    pipeline: str = "animated_explainer",
    repo_dir: str | Path = DEFAULT_OPEN_MONTAGE_DIR,
) -> OpenMontageResult:
    """Convenience function: dispatch a single brief to OpenMontage."""
    adapter = OpenMontageAdapter(repo_dir=repo_dir)
    return adapter.dispatch(brief, pipeline=pipeline)


def _demo() -> None:
    """Exercise the adapter against simulated and real targets."""
    test_brief = "Make a 60-second animated explainer about black holes for high school students."

    print("=== OpenMontage Adapter Test Harness ===")
    print(f"Repo dir: {DEFAULT_OPEN_MONTAGE_DIR}")
    print()

    # 1. Simulate mode
    sim_adapter = OpenMontageAdapter(fallback_on_failure=False)
    sim_result = sim_adapter.dispatch(test_brief, simulate=True)
    print("--- Simulation ---")
    print(f"status={sim_result.status} ok={sim_result.ok}")
    print(f"stdout={sim_result.stdout[:500]}")
    print()

    # 2. Real attempt (fallback to simulation if not available)
    real_adapter = OpenMontageAdapter(fallback_on_failure=True)
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
        id="openmontage",
        name="OpenMontage",
        owner="Open-Montage",
        full_name="Open-Montage/OpenMontage",
        url="https://github.com/Open-Montage/OpenMontage",
    )
    payload = {"brief": test_brief, "pipeline": "animated_explainer", "simulate": True}
    result = asyncio.run(real_adapter.run(node, payload))
    print("--- Async interface ---")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    _demo()
