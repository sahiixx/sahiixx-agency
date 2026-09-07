"""ASGI entrypoint — Lead Machine API + specialized adapter registry.

Prefer this module for uvicorn/Docker/Make:
  uvicorn sahiixx_agency.api.asgi:app --host 0.0.0.0 --port 8082

Wires:
  - /opa/lead/capture|qualify|match|pipeline
  - geomatch + lead_capture into engine._SPECIALIZED_ADAPTERS
"""

from __future__ import annotations

from sahiixx_agency.api.main import app
from sahiixx_agency.api.lead_machine import router as lead_machine_router

# Idempotent router mount
_existing = {getattr(r, "path", None) for r in app.routes}
if "/opa/lead/qualify" not in _existing and "/api/opa/lead/qualify" not in _existing:
    app.include_router(lead_machine_router)

# Mutate module-level specialized adapter map (dispatch routing)
try:
    from sahiixx_agency.core import engine as _engine_mod
    from sahiixx_agency.core.specialized_lead_adapters import register as _register_lead

    _register_lead(_engine_mod._SPECIALIZED_ADAPTERS)
except Exception:  # noqa: BLE001
    pass

__all__ = ["app"]
