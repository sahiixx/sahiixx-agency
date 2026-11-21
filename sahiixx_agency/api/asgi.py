"""ASGI entrypoint — Lead Machine API + specialized adapter registry.

Prefer this module for uvicorn/Docker/Make:
  uvicorn sahiixx_agency.api.asgi:app --host 0.0.0.0 --port 8082

Wires:
  - /opa/lead/capture|qualify|match|pipeline
  - geomatch + lead_capture into engine._SPECIALIZED_ADAPTERS
"""

from __future__ import annotations

from sahiixx_agency.api.lead_machine import router as lead_machine_router
from sahiixx_agency.api.main import app

# Idempotent router mount
_existing = {getattr(r, "path", None) for r in app.routes}
if "/opa/lead/qualify" not in _existing and "/api/opa/lead/qualify" not in _existing:
    app.include_router(lead_machine_router)

# Lead adapters are registered by core.engine for CLI, API, and MCP alike.

__all__ = ["app"]
