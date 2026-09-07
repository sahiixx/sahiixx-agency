# Lead Machine wire-up (apply on merge)

## Already on this branch

- `adapters/lead_capture_agent.py`
- `adapters/geomatch_agent.py`
- `adapters/qualification_agent.py` (was already live)
- `api/lead_machine.py` — `/opa/lead/capture|qualify|match|pipeline`
- `core/specialized_lead_adapters.py` — factories + `register()`
- `config/agency.yaml` — ecosystem + routing for capture / geomatch / agno
- unit tests

## 1. Engine (one inject after `_SPECIALIZED_ADAPTERS`)

After the dict that ends with `"web_intel": _make_web_intel, }` add:

```python
# Lead Machine specialists (geomatch + capture)
try:
    from sahiixx_agency.core.specialized_lead_adapters import register as _register_lead_adapters
    _register_lead_adapters(_SPECIALIZED_ADAPTERS)
except Exception:
    pass
```

## 2. API main.py (two lines)

With the other router imports:

```python
from sahiixx_agency.api.lead_machine import router as lead_machine_router
```

After `app.include_router(panac_router)`:

```python
app.include_router(lead_machine_router)
```

## 3. Smoke

```bash
pytest tests/test_lead_capture_agent.py tests/test_geomatch_agent.py -q
# with server up:
curl -sX POST localhost:8082/opa/lead/qualify -H 'content-type: application/json' \
  -d '{"message":"2BR Marina budget 1.2M buy soon","contact":{"handle":"+9715","channel":"whatsapp"}}'
```

## Endpoints

| Method | Path | Agent |
|--------|------|-------|
| POST | `/opa/lead/capture` | LeadCaptureAgent |
| POST | `/opa/lead/qualify` | QualificationAgent |
| POST | `/opa/lead/match` | GeoMatchAgent |
| POST | `/opa/lead/pipeline` | capture → qualify → match |

(`/api/opa/lead/*` also works via middleware strip.)
