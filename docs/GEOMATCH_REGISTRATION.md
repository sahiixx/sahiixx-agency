# GeoMatch + LeadCapture registration

Prefer **`docs/LEAD_MACHINE_WIRE.md`** (includes API + engine).

## Engine inject

```python
try:
    from sahiixx_agency.core.specialized_lead_adapters import register as _register_lead_adapters
    _register_lead_adapters(_SPECIALIZED_ADAPTERS)
except Exception:
    pass
```

Factories live in `sahiixx_agency/core/specialized_lead_adapters.py`.

## Routing (already in agency.yaml on this branch)

- `lead_machine` / `qualification` → QualificationAgent
- `lead_capture` / `capture` → LeadCaptureAgent
- `geomatch` / `geo_match` → GeoMatchAgent
