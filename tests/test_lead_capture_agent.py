"""Unit tests for LeadCaptureAgent."""

from __future__ import annotations

import asyncio

from sahiixx_agency.adapters.lead_capture_agent import LeadCaptureAgent


def _run(payload):
    return asyncio.get_event_loop().run_until_complete(LeadCaptureAgent().execute(payload))


def test_basic_capture():
    r = _run({"message": "Looking for 2BR in Marina", "contact": {"handle": "+9715", "channel": "whatsapp"}})
    assert r["status"] == "captured"
    assert r["event"] == "lead.created"
    assert r["lead_id"].startswith("lead_")
    assert "Marina" in r["message"]
    assert r["next"] == "qualify"


def test_nexus_whatsapp_fields():
    r = _run({"message": "hi", "wa_id": "971500000", "profile_name": "Ali", "source": "nexus_whatsapp"})
    assert r["contact"]["handle"] == "971500000"
    assert r["source"] == "nexus_whatsapp"
    assert r["contact"]["channel"] == "whatsapp"


def test_empty_message_errors():
    r = _run({"message": ""})
    assert r["status"] == "error"
