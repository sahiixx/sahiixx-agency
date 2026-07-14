from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from sahiixx_agency.core.engine import _SPECIALIZED_ADAPTERS, AgencyEngine
from sahiixx_agency.core.models import AgencyConfig

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "agency.yaml"


@pytest.fixture
def engine():
    data = yaml.safe_load(CONFIG_PATH.read_text())
    config = AgencyConfig(**data)
    return AgencyEngine(config)


def test_all_routing_targets_resolve(engine):
    """Every routing rule target must map to an ecosystem stub or a factory."""
    targets = {rule.target for rule in engine.config.routing_rules}
    unresolved = sorted(
        t for t in targets
        if t not in engine.config.ecosystem and t not in _SPECIALIZED_ADAPTERS
    )
    assert unresolved == [], f"Unresolved routing targets: {unresolved}"


def test_batch4_modules_registered(engine):
    new = [
        "trufflehog",
        "shannon",
        "rag_anything",
        "hermes",
        "chrome_devtools_mcp",
    ]
    for key in new:
        assert key in _SPECIALIZED_ADAPTERS, f"missing factory for {key}"
        assert key in engine.config.ecosystem, f"missing ecosystem stub for {key}"


def test_routing_rule_order_puts_specific_security_before_t3mp3st(engine):
    """trufflehog/shannon rules must precede the broad T3MP3ST security pattern."""
    targets_in_order = [rule.target for rule in engine.config.routing_rules]
    assert targets_in_order.index("trufflehog") < targets_in_order.index("T3MP3ST")
    assert targets_in_order.index("shannon") < targets_in_order.index("T3MP3ST")
