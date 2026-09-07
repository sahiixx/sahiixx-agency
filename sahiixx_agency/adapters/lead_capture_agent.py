"""LeadCaptureAgent: normalize inbound enquiries into LeadCreated events.

First specialist in the Lead Machine. Accepts WhatsApp/NEXUS/web payloads
and returns a stable LeadCreated shape. Does not score or book.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sahiixx_agency.adapters.base import BaseAdapter


class LeadCaptureAgent(BaseAdapter):
    """Normalize raw intake into LeadCreated."""

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        message = (payload.get("message") or payload.get("text") or "").strip()
        if not message:
            return {
                "status": "error",
                "error": "message_required",
                "lead_id": None,
            }

        contact_in = payload.get("contact") or {}
        if isinstance(contact_in, str):
            contact_in = {"handle": contact_in}

        # NEXUS WhatsApp common fields
        handle = (
            contact_in.get("handle")
            or payload.get("wa_id")
            or payload.get("from")
            or payload.get("phone")
            or "unknown"
        )
        name = contact_in.get("name") or payload.get("profile_name") or payload.get("name")
        channel = contact_in.get("channel") or payload.get("channel") or (
            "whatsapp" if payload.get("wa_id") or payload.get("source") == "nexus_whatsapp" else "api"
        )
        source = payload.get("source") or ("nexus_whatsapp" if channel == "whatsapp" else "api")
        lead_id = payload.get("lead_id") or f"lead_{uuid4().hex[:12]}"
        captured_at = payload.get("captured_at") or datetime.now(timezone.utc).isoformat()

        return {
            "lead_id": lead_id,
            "contact": {
                "name": name,
                "handle": str(handle),
                "channel": channel,
            },
            "message": message,
            "source": source,
            "captured_at": captured_at,
            "raw_ref": payload.get("raw_ref") or payload.get("message_id"),
            "status": "captured",
            "next": "qualify",
            "event": "lead.created",
        }
