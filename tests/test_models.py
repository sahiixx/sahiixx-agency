from __future__ import annotations

from sahiixx_agency.core.models import DiscoveryResult, RiskLevel


def test_discovery_result_defaults() -> None:
    dr = DiscoveryResult(full_name="nexu-io/html-anything", url="https://github.com/nexu-io/html-anything")
    assert dr.stars == 0
    assert dr.language == "Unknown"
    assert dr.risk_level == RiskLevel.LOW
    assert dr.source == "discovery"
