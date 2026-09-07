"""Lead Machine HTTP API — direct specialist endpoints for E2E and NEXUS.

Mounted at / (and reachable as /api/* via middleware strip).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["lead-machine"])


class ContactIn(BaseModel):
    name: str | None = None
    handle: str | None = None
    channel: str = "unknown"


class LeadCaptureRequest(BaseModel):
    message: str
    contact: ContactIn | None = None
    source: str = "api"
    raw_ref: str | None = None
    lead_id: str | None = None


class LeadQualifyRequest(BaseModel):
    lead_id: str | None = None
    message: str
    contact: ContactIn | None = None
    source: str = "api"
    captured_at: str | None = None
    raw_ref: str | None = None


class LeadMatchRequest(BaseModel):
    lead_id: str | None = None
    budget_band: str = "unknown"
    intent: str = "buy"
    message: str | None = None
    area_hint: str | None = None
    timeline: str | None = None


@router.post("/opa/lead/capture")
@router.post("/api/opa/lead/capture")
async def capture_lead(body: LeadCaptureRequest) -> dict[str, Any]:
    """Normalize an inbound enquiry into LeadCreated."""
    from sahiixx_agency.adapters.lead_capture_agent import LeadCaptureAgent

    agent = LeadCaptureAgent()
    payload = body.model_dump()
    if body.contact:
        payload["contact"] = body.contact.model_dump()
    try:
        return await agent.execute(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)[:400]) from exc


@router.post("/opa/lead/qualify")
@router.post("/api/opa/lead/qualify")
async def qualify_lead(body: LeadQualifyRequest) -> dict[str, Any]:
    """Score a lead (QualificationAgent) — primary E2E live endpoint."""
    from sahiixx_agency.adapters.qualification_agent import QualificationAgent

    agent = QualificationAgent()
    payload = body.model_dump()
    if body.contact:
        payload["contact"] = body.contact.model_dump()
    payload.setdefault("lead_id", body.lead_id or f"lead_{uuid4().hex[:12]}")
    payload.setdefault("captured_at", body.captured_at or datetime.now(timezone.utc).isoformat())
    try:
        return await agent.execute(payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)[:400]) from exc


@router.post("/opa/lead/match")
@router.post("/api/opa/lead/match")
async def match_lead(body: LeadMatchRequest) -> dict[str, Any]:
    """Attach area matches (GeoMatchAgent)."""
    from sahiixx_agency.adapters.geomatch_agent import GeoMatchAgent

    agent = GeoMatchAgent()
    try:
        return await agent.execute(body.model_dump())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)[:400]) from exc


@router.post("/opa/lead/pipeline")
@router.post("/api/opa/lead/pipeline")
async def lead_pipeline(body: LeadQualifyRequest) -> dict[str, Any]:
    """Capture → qualify → match in one call (sync pipeline for demos/E2E)."""
    from sahiixx_agency.adapters.geomatch_agent import GeoMatchAgent
    from sahiixx_agency.adapters.lead_capture_agent import LeadCaptureAgent
    from sahiixx_agency.adapters.qualification_agent import QualificationAgent

    capture = await LeadCaptureAgent().execute(
        {
            "message": body.message,
            "contact": body.contact.model_dump() if body.contact else None,
            "source": body.source,
            "raw_ref": body.raw_ref,
            "lead_id": body.lead_id,
        }
    )
    qualified = await QualificationAgent().execute(
        {
            **capture,
            "message": body.message,
            "contact": body.contact.model_dump() if body.contact else capture.get("contact"),
        }
    )
    matched = await GeoMatchAgent().execute(
        {
            "lead_id": qualified.get("lead_id") or capture.get("lead_id"),
            "budget_band": qualified.get("budget_band", "unknown"),
            "intent": qualified.get("intent", "buy"),
            "message": body.message,
            "timeline": qualified.get("timeline"),
        }
    )
    return {
        "status": "ok",
        "captured": capture,
        "qualified": qualified,
        "matched": matched,
    }
