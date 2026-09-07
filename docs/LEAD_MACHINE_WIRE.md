# Lead Machine — fully wired

## Entrypoint

Use **`sahiixx_agency.api.asgi:app`** (not `api.main:app`).

`asgi.py` automatically:
1. Mounts `/opa/lead/capture|qualify|match|pipeline`
2. Registers `geomatch` + `lead_capture` into `_SPECIALIZED_ADAPTERS`

Updated: Dockerfile · Makefile · docker-compose.yml · scripts/start.sh

## CLI (`opa serve`)

If you still start via `sahiixx_agency.cli.main`, either:
- `uvicorn sahiixx_agency.api.asgi:app --host 0.0.0.0 --port 8082`
- or change the uvicorn target string in `cli/main.py` from `api.main:app` → `api.asgi:app`

## Smoke

```bash
make serve
# or: uvicorn sahiixx_agency.api.asgi:app --port 8082

curl -sX POST localhost:8082/opa/lead/pipeline \
  -H 'content-type: application/json' \
  -d '{"message":"2BR Marina budget 1.2M buy soon","contact":{"handle":"+9715","channel":"whatsapp"}}'
```
