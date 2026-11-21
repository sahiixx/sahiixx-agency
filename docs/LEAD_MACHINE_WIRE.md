# Lead Machine — local wiring and verification

Verified 2026-11-05. The HTTP pipeline is local capture -> qualification ->
curated offline area matching. It does not book, send WhatsApp messages,
publish lead events to the bus, or import results into the public OS CRM.

## Entrypoint

Use **`sahiixx_agency.api.asgi:app`** (not `api.main:app`).

`asgi.py` automatically:
1. Mounts `/opa/lead/capture|qualify|match|pipeline`
2. Uses the engine's `geomatch` + `lead_capture` registrations in `_SPECIALIZED_ADAPTERS`

Registration lives in the core engine, so CLI and MCP consumers do not depend
on importing the ASGI module first. Failures are no longer silently swallowed.

Updated: Dockerfile · Makefile · docker-compose.yml · scripts/start.sh

## CLI (`opa serve`)

`opa serve --host 127.0.0.1` now targets `sahiixx_agency.api.asgi:app`,
matching Docker and Make. Configure `OPA_API_KEY` before non-local exposure.

## Pipeline contract

- Whitespace-only messages fail request validation with HTTP 422.
- Capture preserves supplied lead IDs, timestamps, source and raw references.
- Direct qualification generates an ID when none is supplied.
- Only `status=qualified` leads invoke matching. Others return `matched: null`.
- Timeline durations longer than three months are exploratory; bare quarter
  labels and unspecified month references remain unknown.
- Exploratory timelines do not earn the near-term scoring bonus. Missing
  budget or timeline prevents high confidence.
- Matching is a static catalogue prior, not a live inventory lookup.
- `next=route_to_scheduling` describes a handoff, not a completed booking.

## Regression checks

```bash
python -m pytest tests/adapters/test_qualification_agent.py tests/test_lead_capture_agent.py tests/test_geomatch_agent.py tests/test_lead_pipeline.py -q
```

Use the project's environment, or an isolated uv environment with the project
and pytest/pytest-asyncio installed. Tests use synthetic leads; the dedicated
HTTP tests avoid the production lifespan and live GitHub synchronization.

## Smoke

```bash
make serve
# or: uvicorn sahiixx_agency.api.asgi:app --port 8082

curl -sX POST localhost:8082/opa/lead/pipeline \
  -H 'content-type: application/json' \
  -d '{"message":"2BR Marina budget 1.2M buy soon","contact":{"handle":"+9715","channel":"whatsapp"}}'
```
