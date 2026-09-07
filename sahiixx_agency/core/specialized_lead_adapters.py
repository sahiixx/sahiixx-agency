"""Lead Machine specialized adapter factories.

Imported by engine._SPECIALIZED_ADAPTERS (see docs/GEOMATCH_REGISTRATION.md).
Also callable as register(dict) to inject keys into an existing registry map.
"""

from __future__ import annotations

from typing import Any, Callable


def _make_geomatch(config, network_policy, audit_logger, task):
    from sahiixx_agency.adapters.geomatch_agent import GeoMatchAgent

    adapter = GeoMatchAgent(
        network_policy=network_policy,
        audit_logger=audit_logger,
    )
    return adapter, dict(task.payload)


def _make_lead_capture(config, network_policy, audit_logger, task):
    from sahiixx_agency.adapters.lead_capture_agent import LeadCaptureAgent

    adapter = LeadCaptureAgent(
        network_policy=network_policy,
        audit_logger=audit_logger,
    )
    return adapter, dict(task.payload)


def register(adapters: dict[str, Callable[..., Any]]) -> None:
    """Inject geomatch + lead_capture into _SPECIALIZED_ADAPTERS in-place."""
    adapters["geomatch"] = _make_geomatch
    adapters["geo_match"] = _make_geomatch
    adapters["geo-match"] = _make_geomatch
    adapters["lead_capture"] = _make_lead_capture
    adapters["lead-capture"] = _make_lead_capture
    adapters["capture"] = _make_lead_capture
