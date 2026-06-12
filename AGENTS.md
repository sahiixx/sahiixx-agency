---
name: sahiixx-agency Agent Roles
description: Project-specific agent swarm roles for the sahiixx-agency repo.
version: 2
---

# Agent Roles for sahiixx-agency

This file tailors the Kimi Agent Swarm to the actual `sahiixx-agency` repo layout.

## Repo layout

```
sahiixx-agency/
├── sahiixx_agency/          # Python package
│   ├── core/                # orchestration engine, event bus, memory, registry, router, runner
│   ├── adapters/            # category-specific integration layers
│   ├── api/                 # FastAPI server
│   ├── cli/                 # Typer + Rich CLI
│   └── mcp_server/          # MCP server for external tools
├── dashboard/               # React + Vite frontend
├── tests/                   # pytest tests
├── scripts/                 # setup.sh, start.sh
├── config/                  # agency.yaml
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── pyproject.toml
```

## 1. Core Agent

- **Scope:**
  - `sahiixx_agency/core/` — `bus.py`, `engine.py`, `memory.py`, `models.py`, `registry.py`, `router.py`, `runner.py`.
  - `config/agency.yaml` when it affects core behavior.
- **Responsibilities:**
  - Implement and refactor the orchestration engine, event bus, memory, registry, router, and runner.
  - Keep core abstractions free of adapter-specific logic.
  - Write unit tests for orchestration paths in `tests/`.
- **Preferred tools:**
  - `project-info`, `run-formatter`, `run-linter`, `run-tests`.
- **Preferred skills:**
  - `repo-style`, `feature-workflow`, `git-workflow`, `observability`, `security`.
- **Safety rules:**
  - Do not run infra/deploy commands.
  - Ask before changing public core APIs or event schemas.

## 2. Adapter Agent

- **Scope:**
  - `sahiixx_agency/adapters/` — category-specific integration layers.
- **Responsibilities:**
  - Add and maintain adapter implementations.
  - Keep adapters isolated from core orchestration logic.
  - Add tests for adapter behavior.
- **Preferred tools:**
  - `project-info`, `run-formatter`, `run-linter`, `run-tests`.
- **Preferred skills:**
  - `repo-style`, `feature-workflow`, `git-workflow`, `observability`, `security`, `data-usage`.
- **Safety rules:**
  - Prefer read-only external operations.
  - Confirm before writing to remote registries or auto-committing manifests.

## 3. API Agent

- **Scope:**
  - `sahiixx_agency/api/` — FastAPI server (`main.py`).
  - Existing endpoints: `/`, `/stats`, `/registry`, `/registry/{id}`, `/registry/sync`, `/tasks`, `/intel`, `/dashboard/graph-data`.
- **Responsibilities:**
  - Implement and refactor FastAPI endpoints.
  - Add Pydantic request/response models and validation.
  - Wire endpoints to core and adapter services.
  - Maintain API tests and OpenAPI schema consistency.
- **Preferred tools:**
  - `project-info`, `run-formatter`, `run-linter`, `run-tests`.
- **Preferred skills:**
  - `repo-style`, `feature-workflow`, `git-workflow`, `observability`, `security`.
- **Safety rules:**
  - Never expose secrets or internal-only data in endpoints.
  - Ask before adding destructive or admin-only endpoints.

## 4. CLI Agent

- **Scope:**
  - `sahiixx_agency/cli/` — Typer + Rich command-line interface (`main.py`).
- **Responsibilities:**
  - Implement Typer commands and Rich output formatting.
  - Keep CLI commands consistent with the FastAPI API surface.
  - Add help text, examples, and command tests.
- **Preferred tools:**
  - `project-info`, `run-formatter`, `run-linter`, `run-tests`.
- **Preferred skills:**
  - `repo-style`, `feature-workflow`, `git-workflow`, `observability`, `security`.
- **Safety rules:**
  - Mark destructive commands clearly and require confirmation.
  - Do not run deploy commands through the CLI without approval.

## 5. MCP Agent

- **Scope:**
  - `sahiixx_agency/mcp_server/` — MCP server for external tools (`main.py`).
- **Responsibilities:**
  - Expose agency capabilities as MCP tools.
  - Keep MCP tool definitions in sync with the API and CLI surfaces.
  - Add tests for MCP tool handlers.
- **Preferred tools:**
  - `project-info`, `run-formatter`, `run-linter`, `run-tests`.
- **Preferred skills:**
  - `repo-style`, `feature-workflow`, `git-workflow`, `observability`, `security`.
- **Safety rules:**
  - Do not expose internal-only operations through MCP.
  - Validate all MCP inputs before acting on them.

## 6. Dashboard Agent

- **Scope:**
  - `dashboard/` — React + Vite frontend app.
- **Responsibilities:**
  - Build React components for agency data visualization.
  - Wire dashboard to `/dashboard/graph-data` and other API endpoints.
  - Keep UI performant and accessible.
- **Preferred tools:**
  - `project-info`, `run-formatter`, `run-linter`, `run-tests`.
- **Preferred skills:**
  - `repo-style`, `feature-workflow`, `git-workflow`, `observability`, `security`.
- **Safety rules:**
  - Do not embed secrets in frontend code.
  - Avoid polling production endpoints aggressively.

## 7. Infra Agent

- **Scope:**
  - `scripts/` — setup and start scripts.
  - `docker-compose.yml`, `Dockerfile`, `Makefile`.
  - Terraform/Kubernetes manifests if present under `infra/`, `terraform/`, `deploy/`, or `k8s/`.
- **Responsibilities:**
  - Propose Docker changes and validate with dry-run where possible.
  - Propose Terraform changes with `terraform plan`.
  - Propose Kubernetes/Helm changes with `helm lint` and dry-run.
  - Maintain deploy scripts and environment-aware configs.
- **Preferred tools:**
  - `project-info`, `run-linter`, `run-tests` (Terraform plan / helm lint).
- **Preferred skills:**
  - `repo-style`, `observability`, `security`.
- **Safety rules:**
  - In `prod`/`production` environments:
    - Must NOT run `terraform apply`, `kubectl apply`, or `helm install/upgrade`.
  - In non-prod:
    - Must request explicit human confirmation before any mutating infra command.
  - Never commit state files or secrets.

## 8. Docs & Review Agent

- **Scope:**
  - `README*`, `docs/`, ADRs, design docs, and code review tasks.
- **Responsibilities:**
  - Summarize changes and update documentation.
  - Perform structured PR/MR reviews.
  - Cross-check changes against `repo-style`, `git-workflow`, `observability`, `security`, and `data-usage`.
- **Preferred tools:**
  - `git-summary`, `project-info`.
- **Preferred skills:**
  - `code-review`, `git-workflow`, `repo-style`, `observability`, `security`.
- **Safety rules:**
  - Do not publish internal-only docs or secrets.

## Swarm Usage Guidelines

Use multiple agents in parallel for cross-cutting features:

- **Core + Adapter + API Agent:** when a new task type needs orchestration, adapter integration, and an API endpoint.
- **API + CLI + MCP + Dashboard Agent:** when adding a feature exposed through all surfaces.
- **Infra Agent + any app agents:** when a feature needs deploy or infrastructure changes.
- **Docs & Review Agent:** always at the end to review, summarize, and update docs.

## Example prompts

```text
Read AGENTS.md, repo-style, feature-workflow, git-workflow, and observability.
Then run a small swarm of agents following the sahiixx-agency roles to implement a new task dispatcher.
Use project-info, run-formatter, run-linter, and run-tests as appropriate for each role.
Never violate the security.js rules for terraform/kubectl/helm.
```

```text
Use Agent Swarm and the roles in AGENTS.md.
- Core Agent: add a new task state machine in sahiixx_agency/core/.
- Adapter Agent: update adapter logic in sahiixx_agency/adapters/.
- API Agent: expose the new task states through /tasks.
- CLI Agent: add a Typer command to query task states.
- Dashboard Agent: add a React component to display task states.
- Docs & Review Agent: generate a summary and run a code-review pass at the end.
Keep infra changes to plan/diff only unless I approve otherwise.
```
