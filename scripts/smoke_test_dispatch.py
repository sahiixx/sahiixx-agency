"""Smoke test: dispatch one intent per high-value module through OPA engine/router.

This script uses the real registry and routing config but mocks external side
effects (LLM calls, subprocess execution, MCP, cloning) so it can run in CI
without hitting the network or spinning up heavy tools.
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Ensure the OPA package is importable from source.
SCRIPT = Path(__file__).resolve()
REPO_ROOT = SCRIPT.parents[1]  # sahiixx-agency root
sys.path.insert(0, str(REPO_ROOT))
# Remove Hermes PYTHONPATH entries so site-packages resolve to the project venv.
for bad in [p for p in sys.path if "hermes-agent" in p]:
    sys.path.remove(bad)
os.environ.pop("PYTHONPATH", None)

from sahiixx_agency.core.engine import AgencyEngine  # noqa: E402
from sahiixx_agency.core.models import AgencyConfig, TaskStatus  # noqa: E402

EXPECTED_ROUTES = {
    "scan target.com for vulnerabilities": {
        "module_id": "T3MP3ST",
        "category": "security",
    },
    "apply to job at https://example.com/job": {
        "module_id": "career-ops",
        "category": "agent_framework",
    },
    "screen resumes for python backend": {
        "module_id": "hiring-agent",
        "category": "agent_framework",
    },
}


async def run_smoke_tests() -> dict:
    """Dispatch sample intents and verify routing + adapter invocation."""
    results = {"summary": {"passed": 0, "failed": 0}, "cases": []}

    # Use a temp directory so we don't pollute the real data dir or clone repos.
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = os.path.join(tmpdir, "data")
        os.makedirs(data_dir, exist_ok=True)

        # Use the real agency.yaml routing config, but point data_dir to tmpdir.
        import yaml

        config_path = REPO_ROOT / "config" / "agency.yaml"
        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        raw.setdefault("data_dir", data_dir)
        config = AgencyConfig.model_validate(raw)

        engine = AgencyEngine(config=config)

        # Mock the external execution paths so nothing is actually cloned/executed.
        with (
            patch(
                "sahiixx_agency.adapters.security.t3mp3st_mcp.T3mp3stMcpAdapter.run",
                new=lambda self, module, payload: asyncio.ensure_future(
                    asyncio.sleep(0, result={
                        "status": "success",
                        "source": "mocked_mcp",
                        "module": module.name,
                        "target": payload.get("target"),
                    })
                ),
            ),
            patch(
                "sahiixx_agency.core.runner.CloneManager.clone",
                new=lambda self, node: Path(self.base_dir) / node.owner / node.name,  # noqa: ARG005
            ),
            patch(
                "sahiixx_agency.core.runner.RepoRunner.run",
                new=lambda self, node, command="run", env=None, timeout=60: {  # noqa: ARG005
                    "status": "success",
                    "source": "mocked_runner",
                    "module": node.name,
                    "command": command,
                },
            ),
        ):
            await engine.start_worker()
            for intent, expected in EXPECTED_ROUTES.items():
                task = await engine.dispatch(intent, payload={"url": intent})
                # Wait for the worker to process the task.
                while task.status not in {TaskStatus.COMPLETED, TaskStatus.FAILED}:
                    await asyncio.sleep(0.05)

                def _norm(name: str) -> str:
                    return name.replace("-", "_").lower()

                route_ok = _norm(task.module_id) == _norm(expected["module_id"]) and task.category.value == expected["category"]
                invoked_ok = task.result and _norm(task.result.get("module", "")) == _norm(expected["module_id"])
                status_ok = task.status == TaskStatus.COMPLETED
                passed = route_ok and invoked_ok and status_ok

                case = {
                    "intent": intent,
                    "expected": expected,
                    "actual": {
                        "module_id": task.module_id,
                        "category": task.category.value if task.category else None,
                        "status": task.status.value,
                        "result_source": task.result.get("source") if task.result else None,
                    },
                    "passed": passed,
                }
                results["cases"].append(case)
                if passed:
                    results["summary"]["passed"] += 1
                else:
                    results["summary"]["failed"] += 1

            await engine.stop_worker()

    return results


def main() -> int:
    """Entry point."""
    results = asyncio.run(run_smoke_tests())

    print("\n=== OPA Dispatcher Smoke Test ===\n")
    for case in results["cases"]:
        status = "PASS" if case["passed"] else "FAIL"
        print(f"[{status}] {case['intent']}")
        print(f"       expected: {case['expected']}")
        print(f"       actual:   {case['actual']}")
    print("\n=== Summary ===")
    print(f"Passed: {results['summary']['passed']}")
    print(f"Failed: {results['summary']['failed']}")

    return 0 if results["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
