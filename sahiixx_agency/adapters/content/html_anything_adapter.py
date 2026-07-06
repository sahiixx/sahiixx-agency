"""Adapter for nexu-io/html-anything — pnpm-workspace Next.js HTML generator."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sahiixx_agency.core.models import RepoNode


@dataclass
class HtmlAnythingResult:
    """Result of running html-anything."""

    ok: bool
    command: str
    returncode: int
    stdout: str
    stderr: str
    url: str = ""
    status: str = ""

    def __post_init__(self) -> None:
        if not self.status:
            self.status = "success" if self.ok else "failed"


class HtmlAnythingAdapter:
    """Run html-anything inside a pnpm monorepo."""

    def __init__(
        self,
        repo_dir: str | Path | None = None,
        clone_base_dir: str | Path | None = None,
        timeout: int = 300,
    ) -> None:
        if repo_dir is None:
            repo_dir = (
                Path(clone_base_dir) / "html-anything"
                if clone_base_dir
                else Path("./data/repos/html-anything").resolve()
            )
        self.repo_dir = Path(repo_dir)
        self.timeout = timeout

    def _run(self, cmd: list[str], cwd: str | Path | None = None) -> HtmlAnythingResult:
        cwd = cwd or self.repo_dir
        command = " ".join(cmd)
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            return HtmlAnythingResult(
                ok=proc.returncode == 0,
                command=command,
                returncode=proc.returncode,
                stdout=proc.stdout[-8000:] if proc.stdout else "",
                stderr=proc.stderr[-4000:] if proc.stderr else "",
                status="success" if proc.returncode == 0 else "error",
            )
        except subprocess.TimeoutExpired as exc:
            return HtmlAnythingResult(
                ok=False,
                command=command,
                returncode=-1,
                stdout=str(exc.stdout or ""),
                stderr=f"Timeout after {self.timeout}s",
                status="timeout",
            )
        except Exception as exc:  # noqa: BLE001
            return HtmlAnythingResult(
                ok=False,
                command=command,
                returncode=-1,
                stdout="",
                stderr=str(exc),
                status="exception",
            )

    def install(self) -> HtmlAnythingResult:
        """Install pnpm workspace dependencies."""
        if not (self.repo_dir / "package.json").exists():
            return HtmlAnythingResult(
                ok=False,
                command="",
                returncode=-1,
                stdout="",
                stderr=f"Repo not found at {self.repo_dir}",
                status="missing_repo",
            )
        return self._run(["pnpm", "install"])

    def dev(self) -> HtmlAnythingResult:
        """Start the Next.js dev server (best effort; returns quickly)."""
        return self._run(["pnpm", "-F", "@html-anything/next", "dev"])

    def generate(self, prompt: str) -> HtmlAnythingResult:
        """Run a headless generate command if available, else start dev server."""
        # html-anything is UI-driven; launch dev server and report URL
        result = self.dev()
        result.url = "http://localhost:3000"
        return result

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        """Agency adapter interface entrypoint."""
        prompt = payload.get("prompt") or payload.get("intent") or ""

        install_result = self.install()
        if not install_result.ok:
            return {
                "module": node.name,
                "status": install_result.status,
                "command": install_result.command,
                "returncode": install_result.returncode,
                "stdout": install_result.stdout,
                "stderr": install_result.stderr,
                "note": "Failed to install dependencies.",
            }

        gen_result = self.generate(prompt)
        return {
            "module": node.name,
            "status": gen_result.status,
            "command": gen_result.command,
            "returncode": gen_result.returncode,
            "stdout": gen_result.stdout,
            "stderr": gen_result.stderr,
            "url": gen_result.url,
            "note": "UI-driven generator. Open the URL and paste your prompt in the browser.",
        }
