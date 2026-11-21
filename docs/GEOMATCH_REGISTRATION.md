# GeoMatch + LeadCapture registration

Prefer **`docs/LEAD_MACHINE_WIRE.md`** (includes API + engine).

## Core engine registration

```python
from sahiixx_agency.core.specialized_lead_adapters import register as register_lead_adapters

register_lead_adapters(_SPECIALIZED_ADAPTERS)
```

Factories live in `sahiixx_agency/core/specialized_lead_adapters.py`.
`core/engine.py` performs registration directly; it does not rely on the ASGI
entrypoint, and registration failures are not silently ignored.

## Routing (already in agency.yaml on this branch)

- `lead_machine` / `qualification` → QualificationAgent
- `lead_capture` / `capture` → LeadCaptureAgent
- `geomatch` / `geo_match` → GeoMatchAgent
