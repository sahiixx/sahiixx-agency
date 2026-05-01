"""Generic repo runner — inspects repo structure and executes modules."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any

import httpx

from .models import RepoNode


class CloneManager:
    """Manages local clones of GitHub repos."""

    def __init__(self, base_dir: str = "./data/repos") -> None:
        self.base_dir = Path(os.path.abspath(base_dir))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def clone_path(self, node: RepoNode) -> Path:
        return self.base_dir / node.owner / node.name

    def is_cloned(self, node: RepoNode) -> bool:
        return self.clone_path(node).joinpath(".git").exists()

    async def clone(self, node: RepoNode) -> Path:
        path = self.clone_path(node)
        if self.is_cloned(node):
            # Pull latest
            subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=60,
            )
            return path

        path.parent.mkdir(parents=True, exist_ok=True)
        clone_url = node.clone_url or f"https://github.com/{node.full_name}.git"
        result = subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, str(path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Clone failed: {result.stderr}")
        return path


class RepoInspector:
    """Inspects a cloned repo to determine how to run it."""

    def __init__(self, repo_path: Path) -> None:
        self.path = repo_path

    def inspect(self) -> dict[str, Any]:
        """Return execution metadata for the repo."""
        result: dict[str, Any] = {
            "runnable": False,
            "type": "unknown",
            "entrypoint": None,
            "package_manager": None,
            "dependencies": False,
            "commands": {},
        }

        # Python detection
        python_files = list(self.path.glob("*.py"))
        if (self.path / "main.py").exists():
            result["runnable"] = True
            result["type"] = "python"
            result["entrypoint"] = "main.py"
            result["commands"]["run"] = ["python", str(self.path / "main.py")]
        elif (self.path / "app.py").exists():
            result["runnable"] = True
            result["type"] = "python"
            result["entrypoint"] = "app.py"
            result["commands"]["run"] = ["python", str(self.path / "app.py")]
        elif (self.path / "run.py").exists():
            result["runnable"] = True
            result["type"] = "python"
            result["entrypoint"] = "run.py"
            result["commands"]["run"] = ["python", str(self.path / "run.py")]
        elif python_files:
            result["runnable"] = True
            result["type"] = "python"
            result["entrypoint"] = python_files[0].name
            result["commands"]["run"] = ["python", str(python_files[0])]

        # Node/TypeScript detection
        if (self.path / "package.json").exists():
            with open(self.path / "package.json", encoding="utf-8") as f:
                pkg = json.load(f)
            scripts = pkg.get("scripts", {})
            result["package_manager"] = "npm"
            if "start" in scripts:
                result["runnable"] = True
                result["type"] = "node"
                result["entrypoint"] = "package.json:start"
                result["commands"]["run"] = ["npm", "start"]
                result["commands"]["install"] = ["npm", "install"]
            elif "dev" in scripts:
                result["runnable"] = True
                result["type"] = "node"
                result["entrypoint"] = "package.json:dev"
                result["commands"]["run"] = ["npm", "run", "dev"]
                result["commands"]["install"] = ["npm", "install"]
            elif "build" in scripts:
                result["runnable"] = True
                result["type"] = "node"
                result["entrypoint"] = "package.json:build"
                result["commands"]["run"] = ["npm", "run", "build"]
                result["commands"]["install"] = ["npm", "install"]

        # Requirements detection
        result["dependencies"] = (
            (self.path / "requirements.txt").exists()
            or (self.path / "pyproject.toml").exists()
            or (self.path / "Pipfile").exists()
            or (self.path / "package.json").exists()
        )

        # Docker detection
        if (self.path / "Dockerfile").exists():
            result["commands"]["docker"] = ["docker", "build", "-t", self.path.name, str(self.path)]

        # Shell script detection
        sh_files = list(self.path.glob("*.sh"))
        if sh_files and not result["runnable"]:
            result["runnable"] = True
            result["type"] = "shell"
            result["entrypoint"] = sh_files[0].name
            result["commands"]["run"] = ["bash", str(sh_files[0])]

        # README for instructions
        readme_candidates = ["README.md", "readme.md", "Readme.md"]
        for cand in readme_candidates:
            if (self.path / cand).exists():
                with open(self.path / cand, encoding="utf-8", errors="ignore") as f:
                    result["readme_preview"] = f.read(500)
                break

        return result


class RepoRunner:
    """Executes repos safely in subprocesses."""

    def __init__(self, clone_manager: CloneManager | None = None) -> None:
        self.clone_manager = clone_manager or CloneManager()

    async def run(
        self,
        node: RepoNode,
        command: str = "run",
        env: dict[str, str] | None = None,
        timeout: int = 60,
    ) -> dict[str, Any]:
        """Clone (if needed), inspect, and run a repo."""
        # Clone
        path = await self.clone_manager.clone(node)

        # Inspect
        inspector = RepoInspector(path)
        meta = inspector.inspect()

        if not meta["runnable"]:
            return {
                "module": node.name,
                "status": "not_runnable",
                "reason": "No recognized entrypoint found",
                "inspection": meta,
            }

        cmd = meta["commands"].get(command)
        if not cmd:
            return {
                "module": node.name,
                "status": "unknown_command",
                "available_commands": list(meta["commands"].keys()),
            }

        # Install dependencies if needed
        if meta["dependencies"] and meta.get("package_manager") == "npm":
            if not (path / "node_modules").exists():
                install_cmd = meta["commands"].get("install", ["npm", "install"])
                subprocess.run(
                    install_cmd,
                    cwd=str(path),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

        # Run
        run_env = {**os.environ, **(env or {})}
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(path),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=run_env,
            )
            return {
                "module": node.name,
                "status": "success" if proc.returncode == 0 else "error",
                "returncode": proc.returncode,
                "stdout": proc.stdout[:5000] if proc.stdout else "",
                "stderr": proc.stderr[:2000] if proc.stderr else "",
                "command": " ".join(shlex.quote(str(c)) for c in cmd),
                "inspection": meta,
            }
        except subprocess.TimeoutExpired:
            return {
                "module": node.name,
                "status": "timeout",
                "command": " ".join(shlex.quote(str(c)) for c in cmd),
            }
        except Exception as exc:
            return {
                "module": node.name,
                "status": "exception",
                "error": str(exc),
            }
