"""HTML-Anything adapter that dispatches layout/design prompts to the cloned repo.

Runs the ``nexu-io/html-anything`` Next.js dev harness from
``data/repos/html-anything``. Since HTML-Anything is an agentic editor that
relies on the AI coding assistant already running inside the browser/CLI, the
adapter's job is to prepare a project brief, surface the right skill, and launch
(or simulate) the local dev server so the agent can continue editing.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sahiixx_agency.core.models import RepoNode

DEFAULT_HTML_ANYTHING_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "repos", "html-anything")
)


@dataclass
class HtmlAnythingResult:
    """Result of dispatching a design/layout brief to HTML-Anything."""

    ok: bool
    brief: str
    surface: str
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


class HtmlAnythingAdapter:
    """Adapter that dispatches a layout brief to the local HTML-Anything repo."""

    def __init__(
        self,
        repo_dir: str | Path | None = None,
        clone_base_dir: str | Path | None = None,
        timeout: int = 300,
        fallback_on_failure: bool = True,
        env: dict[str, str] | None = None,
    ) -> None:
        if repo_dir is None:
            repo_dir = (
                Path(clone_base_dir) / "html-anything"
                if clone_base_dir
                else DEFAULT_HTML_ANYTHING_DIR
            )
        self.repo_dir = Path(repo_dir)
        self.timeout = timeout
        self.fallback_on_failure = fallback_on_failure
        self.env = env or {}

    SURFACES: tuple[str, ...] = (
        "deck",
        "magazine",
        "report",
        "poster",
        "resume",
        "social_post",
        "web_prototype",
        "xiaohongshu",
        "tweet_card",
        "hyperframes_video",
        "landing_page",
    )

    def _infer_surface(self, brief: str) -> str:
        brief_lower = brief.lower()
        surface_keywords = {
            "deck": ["deck", "slide", "presentation", "keynote", "pitch"],
            "magazine": ["magazine", "article", "editorial", "newsletter"],
            "report": ["report", "whitepaper", "one-pager", "data"],
            "poster": ["poster", "flyer", "banner"],
            "resume": ["resume", "cv", "résumé"],
            "social_post": ["social post", "tweet", "x post", "linkedin post", "thread"],
            "web_prototype": ["web", "prototype", "landing page", "landingpage", "site"],
            "xiaohongshu": ["xiaohongshu", "redbook", "red book"],
            "tweet_card": ["tweet card", "twitter card"],
            "hyperframes_video": ["hyperframes", "video"],
        }
        for surface, keywords in surface_keywords.items():
            if any(kw in brief_lower for kw in keywords):
                return surface
        return "web_prototype"

    def _write_brief(self, project_dir: Path, brief: str, surface: str) -> None:
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "brief.txt").write_text(brief, encoding="utf-8")
        (project_dir / "surface.txt").write_text(surface, encoding="utf-8")

    def _find_pnpm(self) -> list[str]:
        """Return the command list to invoke pnpm."""
        import shutil

        pnpm = shutil.which("pnpm")
        if pnpm:
            return [pnpm]
        # Fallback: use npx to run the locally-resolvable pnpm
        return ["npx", "pnpm"]

    def _build_command(self, project_dir: Path, surface: str) -> list[str]:
        """Build command to start the HTML-Anything dev server."""
        next_dir = self.repo_dir / "next"
        if (self.repo_dir / "pnpm-lock.yaml").exists() and next_dir.exists():
            return [*self._find_pnpm(), "-F", "@html-anything/next", "dev"]
        return [
            "python",
            "-c",
            f"print('HTML-Anything project scaffold at {project_dir} for surface {surface}')",
        ]

    def _run_subprocess(self, project_dir: Path, command: list[str]) -> HtmlAnythingResult:
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
            return HtmlAnythingResult(
                ok=proc.returncode == 0,
                brief="",
                surface="",
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
            return HtmlAnythingResult(
                ok=False,
                brief="",
                surface="",
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
            return HtmlAnythingResult(
                ok=False,
                brief="",
                surface="",
                command=command_str,
                returncode=-1,
                stdout="",
                stderr=str(exc),
                cwd=str(self.repo_dir),
                project_dir=str(project_dir),
                status="exception",
                metadata={"timeout": self.timeout, "fallback": False},
            )

    def _simulate(self, project_dir: Path, brief: str, surface: str) -> HtmlAnythingResult:
        """Simulated fallback that returns a deterministic HTML-Anything plan."""
        return HtmlAnythingResult(
            ok=True,
            brief=brief,
            surface=surface,
            command="pnpm -F @html-anything/next dev <simulated>",
            returncode=0,
            stdout=(
                f"[SIMULATED] HTML-Anything production plan\n"
                f"surface: {surface}\n"
                f"project: {project_dir}\n"
                f"skills: 75 available\n"
                f"next_step: open http://localhost:3000 and prompt your agent\n"
            ),
            stderr="",
            cwd=str(self.repo_dir),
            project_dir=str(project_dir),
            status="simulated",
            metadata={"timeout": self.timeout, "fallback": True, "note": "HTML-Anything repo unavailable"},
        )

    def dispatch(
        self,
        brief: str,
        surface: str | None = None,
        project_name: str | None = None,
        simulate: bool = False,
    ) -> HtmlAnythingResult:
        """Dispatch a design/layout brief to HTML-Anything.

        Args:
            brief: Plain-language description of the HTML deliverable to produce.
            surface: Optional surface type (e.g. deck, magazine, landing_page).
            project_name: Optional project directory name.
            simulate: If True, skip the real subprocess and return a simulation.

        Returns:
            HtmlAnythingResult with stdout, stderr, returncode, and status.
        """
        if surface is None:
            surface = self._infer_surface(brief)
        if project_name is None:
            project_name = "".join(c if c.isalnum() else "_" for c in brief[:40]).strip("_")
            if not project_name:
                project_name = "opa_project"
        project_dir = Path(self.repo_dir) / "projects" / project_name
        self._write_brief(project_dir, brief, surface)

        if simulate or not self.repo_dir.exists():
            return self._simulate(project_dir, brief, surface)

        install_result = self._run_subprocess(project_dir, [*self._find_pnpm(), "install"])
        if not install_result.ok:
            if self.fallback_on_failure:
                simulated = self._simulate(project_dir, brief, surface)
                simulated.metadata["original_error"] = install_result.stderr[:500]
                simulated.metadata["original_status"] = install_result.status
                simulated.metadata["note"] = "pnpm install failed"
                return simulated
            return install_result

        command = self._build_command(project_dir, surface)
        result = self._start_dev_server(project_dir, command)
        if not result.ok and self.fallback_on_failure:
            simulated = self._simulate(project_dir, brief, surface)
            simulated.metadata["original_error"] = result.stderr[:500]
            simulated.metadata["original_status"] = result.status
            return simulated
        return result

    def _start_dev_server(self, project_dir: Path, command: list[str]) -> HtmlAnythingResult:
        """Launch the HTML-Anything dev server and verify it accepts traffic.

        The dev server is a long-running process, so it is started with
        ``subprocess.Popen`` and polled on ``localhost:3000``. If the port
        becomes reachable within ``startup_timeout`` seconds the adapter reports
        ``status="running"`` and returns the process pid; otherwise the process
        is terminated and an error result is returned.
        """
        import socket
        import time

        command_str = " ".join(command)
        run_env = {**os.environ, **self.env}
        startup_timeout = 15
        try:
            proc = subprocess.Popen(
                command,
                cwd=str(self.repo_dir),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=run_env,
            )
        except Exception as exc:  # noqa: BLE001
            return HtmlAnythingResult(
                ok=False,
                brief="",
                surface="",
                command=command_str,
                returncode=-1,
                stdout="",
                stderr=str(exc),
                cwd=str(self.repo_dir),
                project_dir=str(project_dir),
                status="exception",
                metadata={"timeout": self.timeout, "fallback": False},
            )

        deadline = time.monotonic() + startup_timeout
        reached = False
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            try:
                with socket.create_connection(("127.0.0.1", 3000), timeout=1):
                    reached = True
                    break
            except OSError:
                time.sleep(0.5)

        if reached:
            return HtmlAnythingResult(
                ok=True,
                brief="",
                surface="",
                command=command_str,
                returncode=0,
                stdout="HTML-Anything dev server listening on http://localhost:3000",
                stderr="",
                cwd=str(self.repo_dir),
                project_dir=str(project_dir),
                status="running",
                metadata={"timeout": self.timeout, "fallback": False, "pid": proc.pid},
            )

        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        return HtmlAnythingResult(
            ok=False,
            brief="",
            surface="",
            command=command_str,
            returncode=proc.returncode if proc.returncode is not None else -1,
            stdout="",
            stderr="Dev server did not start on port 3000",
            cwd=str(self.repo_dir),
            project_dir=str(project_dir),
            status="error",
            metadata={"timeout": self.timeout, "fallback": False},
        )

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        """Conform to the agency adapter interface: run from RepoNode + payload."""
        import asyncio

        brief = payload.get("brief") or payload.get("intent") or ""
        surface = payload.get("surface")
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
            surface=surface,
            project_name=project_name,
            simulate=payload.get("simulate", False),
        )
        return result.metadata | {
            "module": node.name,
            "status": result.status,
            "brief": result.brief,
            "surface": result.surface,
            "project_dir": result.project_dir,
            "command": result.command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": result.cwd,
        }


def run_html_anything(
    brief: str,
    surface: str | None = None,
    repo_dir: str | Path = DEFAULT_HTML_ANYTHING_DIR,
) -> HtmlAnythingResult:
    """Convenience function: dispatch a single brief to HTML-Anything."""
    adapter = HtmlAnythingAdapter(repo_dir=repo_dir)
    return adapter.dispatch(brief, surface=surface)


def _demo() -> None:
    """Exercise the adapter against simulated and real targets."""
    test_brief = "Create a cinematic landing page for a fictional AI wristband called Pulse."

    print("=== HTML-Anything Adapter Test Harness ===")
    print(f"Repo dir: {DEFAULT_HTML_ANYTHING_DIR}")
    print()

    sim_adapter = HtmlAnythingAdapter(fallback_on_failure=False)
    sim_result = sim_adapter.dispatch(test_brief, simulate=True)
    print("--- Simulation ---")
    print(f"status={sim_result.status} ok={sim_result.ok}")
    print(f"stdout={sim_result.stdout[:500]}")
    print()

    real_adapter = HtmlAnythingAdapter(fallback_on_failure=True)
    real_result = real_adapter.dispatch(test_brief)
    print("--- Real dispatch (or fallback) ---")
    print(f"status={real_result.status} ok={real_result.ok}")
    print(f"command={real_result.command}")
    print(f"returncode={real_result.returncode}")
    print(f"stdout={real_result.stdout[:1000]}")
    if real_result.stderr:
        print(f"stderr={real_result.stderr[:500]}")
    print()

    import asyncio

    node = RepoNode(
        id="html-anything",
        name="html-anything",
        owner="nexu-io",
        full_name="nexu-io/html-anything",
        url="https://github.com/nexu-io/html-anything",
    )
    payload = {
        "brief": test_brief,
        "surface": "landing_page",
        "simulate": True,
    }
    result = asyncio.run(real_adapter.run(node, payload))
    print("--- Async interface ---")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    _demo()
