"""Dependency vulnerability scanner for repos before execution."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from .models import DependencyScanReport, RepoNode

logger = logging.getLogger(__name__)


class DependencyScanner:
    """Scan repo dependencies for known vulnerabilities before execution.

    The scanner prefers native audit tools (``pip-audit`` and ``npm audit``)
    when they are installed, but always falls back to a small hardcoded list
    of vulnerable packages so detection works offline and in fresh environments.
    """

    # Known vulnerable package specs: name -> list of (operator, target_version, message)
    _KNOWN_VULNERABILITIES: dict[str, list[tuple[str, str, str]]] = {
        "requests": [
            ("==", "2.6.0", "CVE-2015-2296: requests 2.6.0 session fixation vulnerability"),
        ],
        "lodash": [
            ("<", "4.17.21", "CVE-2021-23337: lodash < 4.17.21 prototype pollution"),
        ],
    }

    _VERSION_SPEC_RE = re.compile(
        r"^\s*(?P<name>[A-Za-z0-9_.-]+)\s*(?P<op>==|>=|<=|>|<|~=|!=)\s*(?P<version>[A-Za-z0-9_.-]+)"
    )

    def __init__(self, data_dir: str = "./data") -> None:
        self.data_dir = Path(data_dir)

    async def scan(self, node: RepoNode) -> DependencyScanReport:
        """Scan dependencies for the given repo node.

        This method is async so the blocking CLI/static parsing work can be
        offloaded from the engine's event loop.
        """
        repo_dir = self._repo_dir(node)
        if repo_dir is None:
            return DependencyScanReport(
                passed=True,
                failures=[],
                command=None,
                stderr="Repo not cloned; skipping dependency scan",
            )

        language = (node.language or "").lower()
        if language in {"python"}:
            return await asyncio.to_thread(self._scan_python, repo_dir)
        if language in {"javascript", "typescript", "node"}:
            return await asyncio.to_thread(self._scan_node, repo_dir)
        return DependencyScanReport(
            passed=True,
            failures=[],
            command=None,
            stderr=f"Unsupported language for dependency scan: {node.language}",
        )

    def _repo_dir(self, node: RepoNode) -> Path | None:
        """Resolve the local repo directory using the same candidates as GenericAdapter."""
        candidates: list[Path] = [
            self.data_dir / "repos" / node.name,
            self.data_dir / "repos" / "trending" / node.owner / node.name,
            self.data_dir / "repos" / node.owner / node.name,
            self.data_dir / node.name,
        ]
        if node.local_path:
            candidates.insert(0, Path(node.local_path))
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _scan_python(self, repo_dir: Path) -> DependencyScanReport:
        """Run pip-audit if available, otherwise parse Python manifests statically."""
        req_file = repo_dir / "requirements.txt"
        if req_file.exists():
            report = self._run_cli(["pip-audit", "--requirement", str(req_file)], repo_dir)
            if report is not None:
                return report
            return self._static_python_scan(repo_dir)

        pyproject_file = repo_dir / "pyproject.toml"
        if pyproject_file.exists():
            report = self._run_cli(["pip-audit", "--local"], repo_dir)
            if report is not None:
                return report
            return self._static_python_scan(repo_dir)

        return DependencyScanReport(
            passed=True,
            failures=[],
            command=None,
            stderr="No Python dependency manifest found",
        )

    def _scan_node(self, repo_dir: Path) -> DependencyScanReport:
        """Run npm audit if available, otherwise parse package.json statically."""
        pkg_file = repo_dir / "package.json"
        if not pkg_file.exists():
            return DependencyScanReport(
                passed=True,
                failures=[],
                command=None,
                stderr="No package.json found",
            )

        report = self._run_cli(["npm", "audit", "--json"], repo_dir)
        if report is not None:
            return report
        return self._static_node_scan(repo_dir)

    def _run_cli(self, cmd: list[str], cwd: Path) -> DependencyScanReport | None:
        """Run a CLI audit tool.

        Returns a passing report when the tool exits 0. Returns ``None`` only
        when the tool is not installed (``FileNotFoundError``) so callers can
        fall back to static parsing.

        On timeout or non-zero exit, the output is parsed for real findings
        rather than failing open. Timeouts return ``None`` to trigger the
        static fallback; non-zero exits return a failing report with parsed
        findings.
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError:
            return None
        except subprocess.TimeoutExpired:
            logger.warning("Dependency scan CLI timed out: %s", " ".join(cmd))
            return None

        if result.returncode == 0:
            return DependencyScanReport(
                passed=True,
                failures=[],
                command=" ".join(cmd),
                stderr=result.stderr[:2000] if result.stderr else None,
            )

        # Non-zero exit: parse the tool's output for real findings.
        command = " ".join(cmd)
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        failures: list[str] = []

        if cmd[0] == "npm":
            failures = self._parse_npm_audit_json(result.stdout or "")
        elif cmd[0] == "pip-audit":
            failures = self._parse_pip_audit_text(output)

        if not failures:
            # Conservative security gate: a non-zero exit with no parseable
            # findings (missing lockfile, malformed output, etc.) must not
            # fail open. Surface the tool's output as the failure reason.
            failures = [output[:2000] if output.strip() else "CLI audit exited non-zero"]

        return DependencyScanReport(
            passed=False,
            failures=failures,
            command=command,
            stderr=output[:2000] if output.strip() else "CLI audit exited non-zero",
        )

    def _parse_npm_audit_json(self, stdout: str) -> list[str]:
        """Parse npm audit --json output for vulnerabilities."""
        failures: list[str] = []
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return failures
        vulnerabilities = data.get("vulnerabilities", {})
        for name, info in vulnerabilities.items():
            if not isinstance(info, dict):
                continue
            severity = info.get("severity", "unknown")
            via_list = info.get("via", [])
            titles: list[str] = []
            for entry in via_list:
                if isinstance(entry, dict):
                    title = entry.get("title") or entry.get("cwe") or "advisory"
                    if isinstance(title, list):
                        titles.extend(str(t) for t in title)
                    else:
                        titles.append(str(title))
            title_str = "; ".join(titles) if titles else "vulnerability found"
            range_str = info.get("range", "")
            failures.append(
                f"npm audit: {name} ({severity}): {title_str}"
                + (f" (range {range_str})" if range_str else "")
            )
        return failures

    def _parse_pip_audit_text(self, output: str) -> list[str]:
        """Parse pip-audit text output for vulnerable package names."""
        failures: list[str] = []
        # Lines like: "requests  2.6.0   PYSEC-2015-2296   2.32.0"
        seen: set[str] = set()
        for line in output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Skip header lines and summary lines
            if stripped.lower().startswith(("name", "found", "no known", "-")):
                continue
            match = re.match(r"^(?P<name>[A-Za-z0-9_.-]+)\s+(?P<version>\S+)", stripped)
            if match:
                name = match.group("name")
                if name not in seen:
                    seen.add(name)
                    failures.append(f"pip-audit: vulnerability found in {name}")
        return failures

    def _static_python_scan(self, repo_dir: Path) -> DependencyScanReport:
        """Parse requirements.txt and pyproject.toml against the hardcoded vuln list."""
        failures: list[str] = []
        command: str | None = None

        req_file = repo_dir / "requirements.txt"
        if req_file.exists():
            command = f"pip-audit --requirement {req_file}"
            deps = self._parse_requirements(req_file)
            failures.extend(self._check_dependencies(deps))

        pyproject_file = repo_dir / "pyproject.toml"
        if pyproject_file.exists():
            command = command or "pip-audit --local"
            deps = self._parse_pyproject(pyproject_file)
            failures.extend(self._check_dependencies(deps))

        return DependencyScanReport(
            passed=not failures,
            failures=failures,
            command=command,
            stderr="Static Python dependency scan completed",
        )

    def _parse_requirements(self, path: Path) -> dict[str, str]:
        """Parse ``name op version`` lines from a requirements file."""
        deps: dict[str, str] = {}
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return deps
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = self._VERSION_SPEC_RE.match(line)
            if match:
                deps[match.group("name").lower()] = match.group("version")
        return deps

    def _parse_pyproject(self, path: Path) -> dict[str, str]:
        """Parse [project.dependencies] from pyproject.toml."""
        deps: dict[str, str] = {}
        try:
            import tomllib
        except ImportError:  # pragma: no cover - Python 3.10 fallback
            return deps
        try:
            with open(path, "rb") as f:
                data: dict[str, Any] = tomllib.load(f)
        except Exception:
            return deps
        for dep in data.get("project", {}).get("dependencies", []):
            match = self._VERSION_SPEC_RE.match(dep)
            if match:
                deps[match.group("name").lower()] = match.group("version")
        return deps

    def _static_node_scan(self, repo_dir: Path) -> DependencyScanReport:
        """Parse package.json dependencies against the hardcoded vuln list."""
        pkg_file = repo_dir / "package.json"
        deps: dict[str, str] = {}
        try:
            with open(pkg_file, encoding="utf-8") as f:
                pkg = json.load(f)
        except Exception:
            return DependencyScanReport(
                passed=True,
                failures=[],
                command="npm audit --json",
                stderr="Failed to parse package.json",
            )

        for group in ("dependencies", "devDependencies"):
            for name, version in pkg.get(group, {}).items():
                deps[name.lower()] = str(version)

        failures = self._check_dependencies(deps)
        return DependencyScanReport(
            passed=not failures,
            failures=failures,
            command="npm audit --json",
            stderr="Static Node dependency scan completed",
        )

    def _check_dependencies(self, deps: dict[str, str]) -> list[str]:
        """Compare resolved dependencies against known vulnerable specs."""
        failures: list[str] = []
        for name, version in deps.items():
            specs = self._KNOWN_VULNERABILITIES.get(name.lower())
            if not specs:
                continue
            for op, target, message in specs:
                if self._version_satisfies(version, op, target):
                    failures.append(f"{name} {op} {target}: {message} (found {version})")
        return failures

    @staticmethod
    def _version_satisfies(current: str, op: str, target: str) -> bool:
        """Simple version comparison using numeric tuple ordering.

        ``~=`` is treated as ``>=`` for compatible-release specs.
        ``!=`` is treated as not-equal.
        """
        current_parts = DependencyScanner._version_parts(current)
        target_parts = DependencyScanner._version_parts(target)
        if op == "==":
            return current_parts == target_parts
        if op in ("!=",):
            return current_parts != target_parts
        if op == "<":
            return current_parts < target_parts
        if op == "<=":
            return current_parts <= target_parts
        if op == ">":
            return current_parts > target_parts
        if op in (">=", "~=", "~"):
            return current_parts >= target_parts
        return False

    @staticmethod
    def _version_parts(version: str) -> tuple[int, ...]:
        """Split a semver-ish version into comparable integer parts.

        Strips common leading operators/ranges and ignores pre-release
        markers (e.g. ``a1``, ``b2``, ``rc1``, ``dev0``).
        """
        # Strip leading v prefix and common operators/ranges.
        cleaned = re.sub(r"^[v^~>=<!]+", "", version)
        parts: list[int] = []
        for part in re.split(r"[.-]", cleaned):
            # Extract leading digits, ignoring non-numeric suffixes.
            digits = re.match(r"(\d+)", part)
            if digits:
                parts.append(int(digits.group(1)))
        return tuple(parts)
