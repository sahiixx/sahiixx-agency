from __future__ import annotations

from sahiixx_agency.core.models import DiscoveryResult, ModuleStatus, RepoCategory, RepoNode, RiskLevel, RoutingRule


def test_discovery_result_defaults() -> None:
    dr = DiscoveryResult(full_name="nexu-io/html-anything", url="https://github.com/nexu-io/html-anything")
    assert dr.stars == 0
    assert dr.language == "Unknown"
    assert dr.risk_level == RiskLevel.LOW
    assert dr.source == "discovery"


def test_repo_node_defaults() -> None:
    node = RepoNode(
        id="html-anything",
        name="html-anything",
        owner="nexu-io",
        full_name="nexu-io/html-anything",
        url="https://github.com/nexu-io/html-anything",
    )
    assert node.stars == 0
    assert node.category == RepoCategory.UNCATEGORIZED
    assert node.status == ModuleStatus.DISCOVERED


def test_routing_rule_validation() -> None:
    rule = RoutingRule(pattern="html|landing", target="html_anything")
    assert rule.pattern == "html|landing"
    assert rule.target == "html_anything"
