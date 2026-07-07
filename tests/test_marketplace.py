from __future__ import annotations

import pytest

from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.marketplace import MarketplaceManager
from sahiixx_agency.core.memory import AgencyMemory
from sahiixx_agency.core.models import (
    AgencyConfig,
    AgencyTask,
    DependencyScanReport,
    MarketplaceListing,
    MarketplaceRating,
    RepoCategory,
    RepoNode,
)
from sahiixx_agency.core.registry import RepoRegistry
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy


def test_marketplace_listing_defaults() -> None:
    node = RepoNode(id="test", name="test", full_name="owner/test", url="https://github.com/owner/test")
    listing = MarketplaceListing(module=node)
    assert listing.install_count == 0
    assert listing.average_rating == 0.0
    assert listing.rating_count == 0
    assert listing.installed_globally is False
    assert listing.enabled_projects == []


def test_marketplace_rating_validation() -> None:
    rating = MarketplaceRating(id="r1", module_id="test", user_id="u1", score=4.5)
    assert rating.score == 4.5


def test_marketplace_rating_rejects_out_of_range() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        MarketplaceRating(id="r1", module_id="test", user_id="u1", score=6.0)


@pytest.fixture
def marketplace(tmp_path) -> MarketplaceManager:
    memory = AgencyMemory(data_dir=str(tmp_path), backend="json")
    registry = RepoRegistry(data_dir=str(tmp_path), github_token=None)
    node = RepoNode(
        id="html-anything",
        name="html-anything",
        full_name="nexu-io/html-anything",
        url="https://github.com/nexu-io/html-anything",
    )
    registry._modules[node.id] = node
    registry.save()
    return MarketplaceManager(registry, memory, data_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_list_modules_returns_registry_modules(marketplace: MarketplaceManager) -> None:
    listings = await marketplace.list_modules()
    assert len(listings) == 1
    assert listings[0].module.id == "html-anything"


@pytest.mark.asyncio
async def test_install_module_clones_and_marks_installed(marketplace: MarketplaceManager, tmp_path) -> None:
    class FakeCloneManager:
        async def clone(self, node):
            path = tmp_path / node.name
            path.mkdir()
            return path

    marketplace.clone_manager = FakeCloneManager()
    listing = await marketplace.install_module("html-anything")
    assert listing.installed_globally is True
    assert listing.install_count == 1


@pytest.mark.asyncio
async def test_enable_and_disable_project(marketplace: MarketplaceManager, tmp_path) -> None:
    class FakeCloneManager:
        async def clone(self, node):
            path = tmp_path / node.name
            path.mkdir()
            return path

    marketplace.clone_manager = FakeCloneManager()
    await marketplace.install_module("html-anything")
    listing = await marketplace.enable_module("html-anything", "project-1")
    assert "project-1" in listing.enabled_projects
    listing = await marketplace.disable_module("html-anything", "project-1")
    assert "project-1" not in listing.enabled_projects


@pytest.mark.asyncio
async def test_rate_module_updates_average(marketplace: MarketplaceManager) -> None:
    await marketplace.rate_module("html-anything", "u1", 5.0)
    await marketplace.rate_module("html-anything", "u2", 3.0)
    listing = (await marketplace.list_modules())[0]
    assert listing.average_rating == 4.0
    assert listing.rating_count == 2


@pytest.mark.asyncio
async def test_get_module_returns_none_for_unknown(marketplace: MarketplaceManager) -> None:
    result = await marketplace.get_module("no-such-module")
    assert result is None


@pytest.mark.asyncio
async def test_list_modules_filters_by_query_and_category(tmp_path) -> None:
    memory = AgencyMemory(data_dir=str(tmp_path), backend="json")
    registry = RepoRegistry(data_dir=str(tmp_path), github_token=None)
    voice_node = RepoNode(
        id="alpha-voice",
        name="alpha-voice",
        full_name="owner/alpha-voice",
        url="https://github.com/owner/alpha-voice",
        category=RepoCategory.VOICE_AI,
    )
    infra_node = RepoNode(
        id="beta-api",
        name="beta-api",
        full_name="owner/beta-api",
        url="https://github.com/owner/beta-api",
        category=RepoCategory.INFRASTRUCTURE,
    )
    registry._modules[voice_node.id] = voice_node
    registry._modules[infra_node.id] = infra_node
    registry.save()
    marketplace = MarketplaceManager(registry, memory, data_dir=str(tmp_path))

    all_listings = await marketplace.list_modules()
    assert len(all_listings) == 2

    voice_listings = await marketplace.list_modules(query="voice")
    assert len(voice_listings) == 1
    assert voice_listings[0].module.id == "alpha-voice"

    infra_listings = await marketplace.list_modules(category=RepoCategory.INFRASTRUCTURE)
    assert len(infra_listings) == 1
    assert infra_listings[0].module.id == "beta-api"

    no_match = await marketplace.list_modules(query="zzz", category=RepoCategory.VOICE_AI)
    assert no_match == []


@pytest.mark.asyncio
async def test_rate_module_replaces_previous_user_rating(marketplace: MarketplaceManager) -> None:
    await marketplace.rate_module("html-anything", "u1", 5.0)
    await marketplace.rate_module("html-anything", "u1", 2.0)
    listing = await marketplace.get_module("html-anything")
    assert listing.average_rating == 2.0
    assert listing.rating_count == 1


@pytest.mark.asyncio
async def test_install_module_blocked_by_network_policy(tmp_path) -> None:
    memory = AgencyMemory(data_dir=str(tmp_path), backend="json")
    registry = RepoRegistry(data_dir=str(tmp_path), github_token=None)
    node = RepoNode(
        id="external-module",
        name="external-module",
        full_name="owner/external-module",
        url="https://github.com/owner/external-module",
        external_hosts=["evil.com"],
    )
    registry._modules[node.id] = node
    registry.save()
    policy = NetworkPolicy(allowlist=["github.com"])
    audit_logger = AuditLogger(memory)
    marketplace = MarketplaceManager(
        registry,
        memory,
        data_dir=str(tmp_path),
        network_policy=policy,
        audit_logger=audit_logger,
    )

    class FakeCloneManager:
        async def clone(self, node):
            path = tmp_path / node.name
            path.mkdir()
            return path

    marketplace.clone_manager = FakeCloneManager()
    with pytest.raises(RuntimeError, match="Network policy blocks"):
        await marketplace.install_module("external-module")


@pytest.mark.asyncio
async def test_install_module_blocked_by_dependency_scan(tmp_path) -> None:
    memory = AgencyMemory(data_dir=str(tmp_path), backend="json")
    registry = RepoRegistry(data_dir=str(tmp_path), github_token=None)
    node = RepoNode(
        id="vuln-module",
        name="vuln-module",
        full_name="owner/vuln-module",
        url="https://github.com/owner/vuln-module",
    )
    registry._modules[node.id] = node
    registry.save()

    class FakeScanner:
        async def scan(self, node):
            return DependencyScanReport(
                passed=False,
                failures=["vulnerability found"],
                command="fake-scan",
                stderr="",
            )

    audit_logger = AuditLogger(memory)
    marketplace = MarketplaceManager(
        registry,
        memory,
        data_dir=str(tmp_path),
        dependency_scanner=FakeScanner(),
        audit_logger=audit_logger,
    )

    class FakeCloneManager:
        async def clone(self, node):
            path = tmp_path / node.name
            path.mkdir()
            return path

    marketplace.clone_manager = FakeCloneManager()
    with pytest.raises(RuntimeError, match="Dependency scan failed"):
        await marketplace.install_module("vuln-module")
    assert marketplace._get_install_count("vuln-module") == 0


@pytest.mark.asyncio
async def test_install_module_raises_for_unknown(marketplace: MarketplaceManager) -> None:
    with pytest.raises(ValueError, match="Module unknown not found"):
        await marketplace.install_module("unknown")


@pytest.mark.asyncio
async def test_enable_module_raises_for_unknown(marketplace: MarketplaceManager) -> None:
    with pytest.raises(ValueError, match="Module unknown not found"):
        await marketplace.enable_module("unknown", "project-1")


@pytest.mark.asyncio
async def test_disable_module_raises_for_unknown(marketplace: MarketplaceManager) -> None:
    with pytest.raises(ValueError, match="Module unknown not found"):
        await marketplace.disable_module("unknown", "project-1")


@pytest.mark.asyncio
async def test_rate_module_raises_for_unknown(marketplace: MarketplaceManager) -> None:
    with pytest.raises(ValueError, match="Module unknown not found"):
        await marketplace.rate_module("unknown", "u1", 3.0)


@pytest.mark.asyncio
async def test_engine_marketplace_filters_routing_by_project(tmp_path) -> None:
    config = AgencyConfig(data_dir=str(tmp_path), memory_backend="json")
    engine = AgencyEngine(config)
    node = RepoNode(
        id="html-anything",
        name="html-anything",
        full_name="nexu-io/html-anything",
        url="https://github.com/nexu-io/html-anything",
        category=RepoCategory.COOKBOOK,
        capabilities=["landing", "page", "html"],
    )
    engine.registry._modules[node.id] = node
    engine.registry.save()

    class FakeCloneManager:
        async def clone(self, node):
            path = tmp_path / node.name
            path.mkdir()
            return path

    engine.marketplace.clone_manager = FakeCloneManager()

    # Without project_id, module is eligible even when not enabled
    task = AgencyTask(id="t1", intent="build a landing page", category=RepoCategory.COOKBOOK)
    candidates = engine.router.score_candidates(task)
    assert any(c.module_id == "html-anything" for c in candidates)

    # With project_id and module not enabled, module is filtered out
    task2 = AgencyTask(id="t2", intent="build a landing page", category=RepoCategory.COOKBOOK, project_id="p1")
    candidates2 = engine.router.score_candidates(task2)
    assert not any(c.module_id == "html-anything" for c in candidates2)

    # After enabling for project, module is eligible again
    await engine.marketplace.enable_module("html-anything", "p1")
    candidates3 = engine.router.score_candidates(task2)
    assert any(c.module_id == "html-anything" for c in candidates3)
