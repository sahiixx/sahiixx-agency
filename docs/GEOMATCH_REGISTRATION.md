# GeoMatchAgent — Registration (v2.1)

`sahiixx_agency/adapters/geomatch_agent.py` is on this branch.

QualificationAgent is **already** registered as `lead_machine` / `qualification`.
Apply the following for GeoMatch.

## 1. `sahiixx_agency/core/engine.py`

After `_make_lead_machine`, add:

```python
def _make_geomatch(config, network_policy, audit_logger, task):
    from sahiixx_agency.adapters.geomatch_agent import GeoMatchAgent

    adapter = GeoMatchAgent(
        network_policy=network_policy,
        audit_logger=audit_logger,
    )
    return adapter, dict(task.payload)
```

In `_SPECIALIZED_ADAPTERS`, add:

```python
    "geomatch": _make_geomatch,
    "geo_match": _make_geomatch,
    "geo-match": _make_geomatch,
```

## 2. `config/agency.yaml`

### Ecosystem entry (after `lead_machine`)

```yaml
  geomatch:
    repo: sahiixx-agency
    url: https://github.com/sahiixx/sahiixx-agency
    role: "GeoMatchAgent — area/property matching for qualified Dubai RE leads"
    capabilities: [geo-match, area-recommendation, inventory-match, lead-matched]
    category: real_estate
    bus_channel: "lead.*"
    protocol: internal
    priority: 1
    tags: [dubai, real-estate, geomatch, lead-machine]
```

### Routing rule (near lead_machine rule)

```yaml
  - pattern: "match.*(lead|property|area)|geomatch|geo.?match|area match|property match|recommend.*(area|community|listing)"
    target: geomatch
```

(Optional: narrow the existing lead_machine pattern so `match.*property` does not steal geomatch traffic.)

## 3. Verify

```bash
pytest tests/test_geomatch_agent.py -q
opa dispatch "match property areas for marina budget 1.2M"
```

## Status

| Agent | Code | Registry | Routing |
|-------|------|----------|---------|
| QualificationAgent | live | live (`lead_machine`) | live |
| GeoMatchAgent | this PR | apply snippet above | apply snippet above |
