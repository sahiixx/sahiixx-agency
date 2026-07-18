"""Tests for portfolio entry drafting and rendering."""

from __future__ import annotations

import json

import pytest

from sahiixx_agency.adapters.portfolio_entry import (
    ProjectEntry,
    entry_from_response,
    next_index,
    render_ts_entry,
    slugify,
)

MODULE = {
    "id": "postiz-app",
    "name": "postiz-app",
    "description": "Social media scheduling tool",
    "language": "TypeScript",
    "url": "https://github.com/sahiixx/postiz-app",
}

ENTRY_JSON = json.dumps({
    "name": "Postiz",
    "tagline": "Schedule everything, everywhere.",
    "description": "A social scheduling pipeline with queue workers and channel adapters.",
    "longDescription": [
        "Paragraph one, long enough to force the multi-line array rendering branch.",
        "Paragraph two, also long enough for the same rendering branch.",
    ],
    "problem": "Posting to five networks by hand does not scale.",
    "architecture": "Next.js · workers · Redis queues",
    "statusNote": "Running locally.",
    "highlights": ["Multi-channel", "Queue-based", "Self-hosted"],
    "role": "Architect & sole engineer",
    "status": "Shipped",
    "stack": ["TypeScript", "Next.js", "Redis"],
    "url": "https://github.com/sahiixx/postiz-app",
})


def test_slugify():
    assert slugify("postiz-app") == "postiz-app"
    assert slugify("SAHIIX OS") == "sahiix-os"
    assert slugify("deer_flow 2.0") == "deer-flow-2-0"


def test_next_index():
    assert next_index(["01", "02", "04"]) == "05"
    assert next_index([]) == "01"


def test_entry_from_response_fills_caller_fields():
    entry = entry_from_response(ENTRY_JSON, module=MODULE, index="05", accent="#34d399", year="2026")
    assert entry.id == "postiz-app"
    assert entry.index == "05"
    assert entry.accent == "#34d399"
    assert entry.year == "2026"
    assert entry.name == "Postiz"


def test_entry_from_response_strips_prose_around_json():
    raw = "Here is your entry:\n```json\n" + ENTRY_JSON + "\n```\nDone."
    entry = entry_from_response(raw, module=MODULE, index="05", accent="#34d399", year="2026")
    assert entry.id == "postiz-app"


def test_entry_from_response_rejects_missing_fields():
    with pytest.raises(Exception):
        entry_from_response('{"name": "X"}', module=MODULE, index="05", accent="#34d399", year="2026")


def test_render_ts_entry_matches_data_ts_style():
    entry = entry_from_response(ENTRY_JSON, module=MODULE, index="05", accent="#34d399", year="2026")
    rendered = render_ts_entry(entry)
    assert rendered.startswith("  {\n")
    assert rendered.endswith("  },")
    assert '    id: "postiz-app",' in rendered
    assert '    index: "05",' in rendered
    assert '    accent: "#34d399",' in rendered
    assert "    longDescription: [\n" in rendered
    # no optional fields rendered
    assert "featured" not in rendered
    assert "image" not in rendered


def test_entry_from_response_overrides_llm_id_and_url():
    data = json.loads(ENTRY_JSON)
    data["id"] = "evil-llm-slug"
    data["url"] = "https://github.com/wrong-org/nope"
    entry = entry_from_response(json.dumps(data), module=MODULE, index="05", accent="#34d399", year="2026")
    assert entry.id == "postiz-app"
    assert entry.url == "https://github.com/sahiixx/postiz-app"


def test_render_ts_entry_inlines_five_item_arrays():
    data = json.loads(ENTRY_JSON)
    data["stack"] = ["A", "B", "C", "D", "E"]
    entry = entry_from_response(json.dumps(data), module=MODULE, index="05", accent="#34d399", year="2026")
    rendered = render_ts_entry(entry)
    assert 'stack: ["A", "B", "C", "D", "E"]' in rendered
