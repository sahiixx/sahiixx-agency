"""Infer how to run a cloned repository."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        return {}


def detect_project_type(repo_dir: str | Path) -> str:
    """Detect the dominant project type in a repo directory."""
    repo = Path(repo_dir)
    if (repo / "package.json").exists():
        return "node"
    if (repo / "pyproject.toml").exists() or (repo / "requirements.txt").exists():
        return "python"
    if (repo / "Dockerfile").exists() or (repo / "docker-compose.yml").exists():
        return "docker"
    if (repo / "Makefile").exists():
        return "make"
    if any((repo / name).exists() for name in ("main.py", "app.py", "run.py")):
        return "python"
    return "unknown"


def _node_entrypoint(repo: Path) -> list[list[str]] | None:
    package = _read_json(repo / "package.json")
    scripts = package.get("scripts", {})
    for script in ("dev", "start", "serve", "run"):
        if script in scripts:
            return [["npm", "install"], ["npm", "run", script]]
    return [["npm", "install"], ["npm", "start"]]


def _python_entrypoint(repo: Path) -> list[list[str]] | list[str] | None:
    for script in ("main.py", "app.py", "run.py"):
        if (repo / script).exists():
            install_cmd: list[list[str]] | list[str] = (
                [["pip", "install", "-e", "."]]
                if (repo / "pyproject.toml").exists()
                else [["pip", "install", "-r", "requirements.txt"]]
                if (repo / "requirements.txt").exists()
                else []
            )
            if install_cmd:
                return [*install_cmd, ["python", script]]
            return ["python", script]
    return None


def _make_entrypoint(repo: Path) -> list[str] | None:
    makefile = (repo / "Makefile").read_text(encoding="utf-8")
    for target in ("run", "start", "dev", "all"):
        if f"{target}:" in makefile:
            return ["make", target]
    return ["make"]


def _docker_entrypoint(repo: Path) -> list[list[str]] | None:
    return [
        ["docker", "build", "-t", repo.name, "."],
        ["docker", "run", "--rm", repo.name],
    ]


def infer_entrypoint(repo_dir: str | Path) -> list[list[str]] | list[str] | None:
    """Return the best-effort command(s) to run a repo."""
    repo = Path(repo_dir)
    if not repo.is_dir():
        return None
    project_type = detect_project_type(repo)
    handlers = {
        "node": _node_entrypoint,
        "python": _python_entrypoint,
        "make": _make_entrypoint,
        "docker": _docker_entrypoint,
    }
    handler = handlers.get(project_type)
    return handler(repo) if handler else None
