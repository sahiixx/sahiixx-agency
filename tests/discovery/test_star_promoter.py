from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sahiixx_agency.discovery import star_promoter as sp

CONFIG = Path(__file__).resolve().parents[2] / "config" / "agency.yaml"


@pytest.fixture
def sample_stars():
    return [
        {
            "full_name": "google/adk-python",
            "name": "adk-python",
            "owner": "google",
            "html_url": "https://github.com/google/adk-python",
            "description": "Google Agent Development Kit for building agents",
        },
        {
            "full_name": "trufflesecurity/trufflehog",
            "name": "trufflehog",
            "owner": "trufflesecurity",
            "html_url": "https://github.com/trufflesecurity/trufflehog",
            "description": "Find and remediate leaked credentials and secrets",
        },
        {
            "full_name": "someuser/awesome-video-tool",
            "name": "awesome-video-tool",
            "owner": "someuser",
            "html_url": "https://github.com/someuser/awesome-video-tool",
            "description": "A tool to montage and edit videos",
        },
    ]


def test_classify_category_specific_before_generic():
    assert sp.classify_category({"full_name": "x/trufflehog", "description": "secret scanner"}) == "security"
    assert sp.classify_category({"full_name": "x/adk-python", "description": "agent development kit"}) == "framework"
    assert sp.classify_category({"full_name": "x/foo", "description": "random thing"}) == "framework"


def test_build_ecosystem_entry_shape():
    key, entry = sp.build_ecosystem_entry(
        {"full_name": "google/adk-python", "html_url": "https://github.com/google/adk-python", "description": "ADK"}
    )
    assert key == "adk_python"
    assert entry["owner"] == "google"
    assert entry["protocol"] == "python-lib"
    assert entry["bus_channel"] == "framework.*"


def test_build_routing_rule_escapes():
    rule = sp.build_routing_rule("adk_python", {"full_name": "google/adk-python"})
    assert rule["target"] == "adk_python"
    assert "adk" in rule["pattern"]
    assert "google" in rule["pattern"]


def test_generate_promotions_skips_existing(sample_stars):
    existing_keys = {"adk_python"}
    existing_targets = set()
    out = sp.generate_promotions(sample_stars, existing_keys, existing_targets)
    assert "adk_python" not in out["ecosystem"]
    assert "trufflehog" in out["ecosystem"]
    assert "awesome_video_tool" in out["ecosystem"]
    targets = {r["target"] for r in out["routing_rules"]}
    assert "trufflehog" in targets


def test_generate_promotions_dedups_same_key(sample_stars):
    # Duplicate name should not appear twice.
    stars = sample_stars + [dict(sample_stars[1])]
    out = sp.generate_promotions(stars, set(), set())
    assert list(out["ecosystem"]).count("trufflehog") == 1


def test_render_yaml_contains_entries(sample_stars):
    out = sp.generate_promotions(sample_stars, {"adk_python"}, set())
    text = sp.render_yaml(out)
    assert "trufflehog:" in text
    assert "awesome_video_tool:" in text
    assert "target: trufflehog" in text


def test_load_existing_reads_config():
    keys, targets = sp.load_existing(str(CONFIG))
    assert "trufflehog" in keys
    assert "shannon" in keys
    assert "T3MP3ST" in targets


def test_apply_to_agency_yaml_stays_valid(tmp_path, sample_stars):
    """--write must produce a YAML file that still parses and contains new keys."""
    target = tmp_path / "agency.yaml"
    target.write_text(CONFIG.read_text(), encoding="utf-8")
    additions = sp.generate_promotions(sample_stars, set(), set())
    written = sp.apply_to_agency_yaml(str(target), additions)
    assert written == 3
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert "trufflehog" in data["ecosystem"]
    assert "awesome_video_tool" in data["ecosystem"]
    targets = {r["target"] for r in data["routing_rules"]}
    assert "trufflehog" in targets
    assert "awesome_video_tool" in targets


@pytest.mark.asyncio
async def test_fetch_stars_offline_safe(monkeypatch):
    import httpx

    def boom(*args, **kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("sahiixx_agency.discovery.star_promoter.httpx.AsyncClient.get", boom)
    result = await sp.fetch_stars("sahiixx", token="x")
    assert result == []
