# OPA Phase 3 — Production Hardening Plan

**Date:** 2026-07-07
**Status:** Active — Phase 1 command center complete, Phase 2 autonomy scaffolded, now hardening for production.

## Global Constraints

- Target Python 3.11+, Pydantic v2, FastAPI, Typer, Rich, React + Tailwind.
- All new code must have type hints and tests.
- Do not break existing 208 passing tests.
- Do not commit or push — this is a working-tree-only run.
- Review packages are generated from `git diff HEAD -- <changed-files>`.
- Stop if disk free drops below 1GB.

## Current State

Phase 1 (command center) and Phase 2 (scheduler + LTM stubs) are complete:
- Chat API, approvals, task stream, dashboard wiring, CLI, Telegram, LLM, workflows, notifications, metrics, security scaffolding, multi-tenancy scaffolding.
- 208 tests passing.

## Task 1: Enforce NetworkPolicy in RepoRunner

**Goal:** Make the network egress policy real by blocking outbound connections to non-allowed hosts during repo execution.

**What to do:**
- Read `sahiixx_agency/core/runner.py` and `sahiixx_agency/core/security.py`.
- Modify `RepoRunner.run()` to accept an optional `network_policy: NetworkPolicy`.
- Before running a repo, if a network policy is provided and the module declares external hosts it will call, verify each host against the policy.
- If a host is blocked, raise a `RuntimeError` with a clear message and log an audit event.
- If the policy allows all (default), run normally.
- Add `network_policy` field to `RepoNode` or pass it via payload.
- Add tests in `tests/test_runner.py` or `tests/test_security.py` covering allowed/blocked hosts and default-allow behavior.
- Run `pytest tests/test_security.py tests/test_runner.py` and ensure passing.

**Definition of done:**
- `RepoRunner.run()` respects `NetworkPolicy`.
- Tests prove blocked hosts raise and allowed hosts pass.
- Existing tests still pass.

## Task 2: Dependency Vulnerability Scanning

**Goal:** Add a safety check that scans repo dependencies before execution.

**What to do:**
- Create `sahiixx_agency/core/dependency_scanner.py` with a `DependencyScanner` class.
- Detect repo language from `RepoNode.language`.
- For Python repos, run `pip-audit --requirement requirements.txt` or `pip-audit --local` if available; fall back to parsing `requirements.txt`/`pyproject.toml` for known vulnerable packages (use a small hardcoded list of bad packages/versions for the scaffold).
- For Node repos, run `npm audit --json` if available; fall back to parsing `package.json` for known vulnerable packages.
- Return a scan report: `passed`, `failures` list, `command`, `stderr`.
- Integrate into `AgencyEngine._execute_task()` before running a repo when `config.security.dependency_scan_enabled` is true (add this flag to `SecurityConfig`).
- If scan fails, mark task as failed with the report in `task.result` and log audit event.
- Add tests in `tests/test_dependency_scanner.py`.
- Run `pytest tests/test_dependency_scanner.py`.

**Definition of done:**
- `DependencyScanner` exists and handles Python/Node.
- Engine blocks execution when scan fails.
- Tests pass.

## Task 3: Structured JSON Logs Per Task

**Goal:** Replace/adjoin ad-hoc memory events with structured task logs.

**What to do:**
- Create `sahiixx_agency/core/logger.py` with a `TaskLogger`.
- Each log entry is JSON with: `timestamp`, `level`, `task_id`, `actor`, `message`, `extra`.
- Persist logs to `data/task-logs/{task_id}.jsonl` (append-only).
- Add methods: `log(task_id, level, message, **extra)`, `info`, `warning`, `error`.
- Integrate into `AgencyEngine._execute_task()` to log lifecycle events: dispatch, start, complete, fail.
- Integrate into approval actions and chat dispatch.
- Add `GET /tasks/{task_id}/logs` endpoint returning the JSONL lines as JSON array.
- Add tests in `tests/test_task_logger.py`.
- Run `pytest tests/test_task_logger.py tests/test_api.py`.

**Definition of done:**
- Task logs are written for task lifecycle events.
- `/tasks/{task_id}/logs` returns them.
- Tests pass.

## Task 4: Per-Project Cost Tracking

**Goal:** Track agency costs per tenant/project.

**What to do:**
- Extend `AgencyMemory` or add a `CostLedger` class in `sahiixx_agency/core/costs.py`.
- Store cost records with: `tenant_id`, `project_id`, `task_id`, `category`, `amount`, `currency`, `description`, `timestamp`.
- Integrate into `LLMCostTracker` so each LLM call is attributed to a task's tenant/project.
- Integrate into task dispatch so adapter runs can also record estimated cost (optional).
- Add endpoints:
  - `GET /costs?tenant_id=&project_id=` — list cost records
  - `GET /costs/summary?tenant_id=&project_id=` — aggregate by category
- Add CLI commands:
  - `opa costs --tenant <id>`
  - `opa costs --project <id>`
- Add tests in `tests/test_costs.py`.
- Run `pytest tests/test_costs.py tests/test_llm.py tests/test_cli.py`.

**Definition of done:**
- Costs are attributed to tenant/project.
- API and CLI expose cost data.
- Tests pass.

## Task 5: White-Label Dashboard Configuration

**Goal:** Allow per-tenant/per-project branding of the dashboard.

**What to do:**
- Add `/config/white-label` endpoint that serves a JSON config: `{brandName, logoUrl, primaryColor, faviconUrl}`.
- Default values point to "One Person Agency" branding.
- Store white-label config per project in memory (`project:{id}:white_label`).
- Update dashboard to read `/config/white-label` on load and apply brand name and primary color.
- Add tests in `tests/test_api.py`.
- Run `pytest tests/test_api.py`.

**Definition of done:**
- Dashboard loads white-label config.
- API serves per-project config.
- Tests pass.

## Task 6: Production Docker Compose Packaging

**Goal:** Update packaging for production deployment.

**What to do:**
- Update `docker-compose.yml` to include API, MCP server, dashboard (static served by API), and a persistent volume for `./data`.
- Add a `Dockerfile` if missing or improve the existing one.
- Add `.dockerignore` to exclude `node_modules`, `.venv`, `data`, `tmp`.
- Add healthchecks in compose.
- Add a `scripts/start-production.sh` helper.
- Do not build the image (disk constrained) — just validate the files are syntactically correct.

**Definition of done:**
- `docker-compose.yml` describes production services.
- Files are valid YAML/shell.

## Verification

After all tasks:
- `pytest tests/` exits 0.
- Dashboard builds and screenshot shows updated UI.
- Server starts and health endpoint returns healthy.
