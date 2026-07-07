"""Tests for the One Person Agency core."""

import asyncio
from typing import Any

import pytest

from sahiixx_agency.adapters.security.t3mp3st_mcp import T3mp3stMcpAdapter
from sahiixx_agency.core.bus import MessageBus
from sahiixx_agency.core.engine import AgencyEngine
from sahiixx_agency.core.models import AgencyConfig, AgencyTask, RepoCategory, RepoNode, TaskStatus
from sahiixx_agency.core.registry import RepoRegistry, _classify_repo
from sahiixx_agency.core.router import TaskRouter


def test_agency_config_loads_t3mp3st_approval_token():
    config = AgencyConfig(t3mp3st_approval_token="super-secret")
    assert config.t3mp3st_approval_token == "super-secret"


def test_new_repo_categories_exist():
    assert RepoCategory.CONTENT_MEDIA.value == "content_media"
    assert RepoCategory.KNOWLEDGE.value == "knowledge"
    assert RepoCategory.CAREER.value == "career"

POLL_MAX_ATTEMPTS = 40
POLL_INTERVAL = 0.25

FAKE_MODULES = [
    RepoNode(
        id="echo-module",
        name="echo-module",
        full_name="sahiixx/echo-module",
        url="https://github.com/sahiixx/echo-module",
        category=RepoCategory.AGENT_FRAMEWORK,
        language="python",
        stars=10,
        capabilities=["echo"],
    ),
    RepoNode(
        id="friday",
        name="friday",
        full_name="sahiixx/friday",
        url="https://github.com/sahiixx/friday",
        category=RepoCategory.VOICE_AI,
        language="python",
        stars=50,
        capabilities=["voice"],
    ),
]


@pytest.fixture
def engine(tmp_path, monkeypatch):
    config = AgencyConfig(data_dir=str(tmp_path))
    eng = AgencyEngine(config)

    async def fake_discover(username):
        for mod in FAKE_MODULES:
            eng.registry._modules[mod.id] = mod
        return FAKE_MODULES

    async def fake_run(module, command="run", env=None, timeout=60):
        return {
            "module": module.name,
            "status": "success",
            "returncode": 0,
            "stdout": "ok",
            "stderr": "",
            "command": command,
        }

    monkeypatch.setattr(eng.registry, "discover", fake_discover)
    monkeypatch.setattr(eng.runner, "run", fake_run)
    return eng


@pytest.mark.asyncio
async def test_sync_repos(engine):
    discovered = await engine.sync_repos("sahiixx")
    assert len(discovered) == 2
    assert engine.registry.stats()["total_modules"] == 2


@pytest.mark.asyncio
async def test_dispatch_task(engine):
    await engine.start_worker()
    try:
        await engine.sync_repos("sahiixx")
        task = await engine.dispatch("run voice assistant")
        assert task.id is not None
        assert task.status.value == "pending"
        # Poll for terminal status
        for _ in range(POLL_MAX_ATTEMPTS):
            current = engine.get_task(task.id)
            if current.status.value in ("completed", "failed"):
                break
            await asyncio.sleep(POLL_INTERVAL)
        final = engine.get_task(task.id)
        assert final.status.value in ("completed", "failed")
    finally:
        await engine.stop_worker()


def test_registry_stats(engine):
    stats = engine.registry.stats()
    assert "total_modules" in stats
    assert "by_category" in stats


@pytest.mark.asyncio
async def test_intel_scout(engine, monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"items": []}

    async def fake_get(self, url, **kwargs):
        return FakeResponse()

    monkeypatch.setattr("httpx.AsyncClient.get", fake_get)
    report = await engine.run_intel_scout("trending")
    assert report.id is not None
    assert len(report.repos) >= 0


@pytest.mark.asyncio
async def test_execute_module(engine):
    await engine.sync_repos("sahiixx")
    module = engine.registry.modules[0]
    result = await engine.runner.run(module, timeout=15)
    assert "status" in result
    assert result["module"] == module.name


@pytest.fixture
def config(tmp_path):
    return AgencyConfig(data_dir=str(tmp_path))


@pytest.fixture
def fake_registry():
    class FakeRegistry:
        def __init__(self) -> None:
            self.modules: list[RepoNode] = []

        def get(self, module_id: str) -> RepoNode | None:
            return next((m for m in self.modules if m.id == module_id), None)

        def set_status(self, module_id: str, status: Any) -> None:
            pass

        def stats(self) -> dict[str, Any]:
            return {"total_modules": len(self.modules)}

    return FakeRegistry()


def test_get_task_unknown_id(engine):
    assert engine.get_task("task_does_not_exist") is None


@pytest.mark.asyncio
async def test_list_tasks_returns_recent_tasks(engine):
    await engine.start_worker()
    try:
        await engine.sync_repos("sahiixx")
        task1 = await engine.dispatch("run voice assistant")
        task2 = await engine.dispatch("run voice assistant")
        tasks = engine.list_tasks(limit=10)
        ids = {t.id for t in tasks}
        assert task1.id in ids
        assert task2.id in ids
    finally:
        await engine.stop_worker()


@pytest.fixture
def router_with_new_modules(tmp_path):
    config = AgencyConfig(
        data_dir=str(tmp_path),
        routing_rules=[
            {"pattern": "t3mp3st|red.team|offensive|0-day|zero.day|exploit|pentest|recon|security", "target": "t3mp3st"},
            {"pattern": "resume|candidate|hire|hiring|evaluate.profile|screen|recruit", "target": "hiring_agent"},
        ],
        ecosystem={
            "t3mp3st": {
                "repo": "T3MP3ST",
                "owner": "elder-plinius",
                "url": "https://github.com/elder-plinius/T3MP3ST",
                "role": "red-team meta-harness",
            },
            "hiring_agent": {
                "repo": "hiring-agent",
                "owner": "interviewstreet",
                "url": "https://github.com/interviewstreet/hiring-agent",
                "role": "AI hiring agent",
            },
        },
    )
    registry = RepoRegistry(data_dir=str(tmp_path))
    registry._modules["t3mp3st"] = RepoNode(
        id="t3mp3st",
        name="T3MP3ST",
        full_name="elder-plinius/T3MP3ST",
        url="https://github.com/elder-plinius/T3MP3ST",
        category=RepoCategory.SECURITY,
    )
    registry._modules["hiring_agent"] = RepoNode(
        id="hiring_agent",
        name="hiring-agent",
        full_name="interviewstreet/hiring-agent",
        url="https://github.com/interviewstreet/hiring-agent",
        category=RepoCategory.UNCATEGORIZED,
    )
    return TaskRouter(registry, MessageBus(), config=config)


@pytest.mark.asyncio
async def test_router_resolves_red_team_intent_to_t3mp3st(router_with_new_modules):
    task = await router_with_new_modules.route("run a pentest recon against example.com")
    assert task.module_id == "t3mp3st"


@pytest.mark.asyncio
async def test_router_resolves_hiring_intent_to_hiring_agent(router_with_new_modules):
    task = await router_with_new_modules.route("evaluate this candidate's resume")
    assert task.module_id == "hiring_agent"


@pytest.mark.asyncio
async def test_execute_task_uses_t3mp3st_adapter(tmp_path, monkeypatch):
    config = AgencyConfig(
        data_dir=str(tmp_path),
        t3mp3st_approval_token="super-secret",
    )
    engine = AgencyEngine(config)

    module = RepoNode(
        id="t3mp3st",
        name="T3MP3ST",
        owner="elder-plinius",
        full_name="elder-plinius/T3MP3ST",
        url="https://github.com/elder-plinius/T3MP3ST",
        category=RepoCategory.SECURITY,
    )
    engine.registry._modules["t3mp3st"] = module

    adapter_calls: list[tuple[str, dict[str, Any]]] = []

    async def fake_adapter_run(self, mod, payload):
        adapter_calls.append((mod.id, payload))
        return {"status": "success", "source": "adapter"}

    monkeypatch.setattr(T3mp3stMcpAdapter, "run", fake_adapter_run)

    task = AgencyTask(
        id="task_test_t3mp3st",
        intent="run t3mp3st against example.com",
        module_id="t3mp3st",
        payload={"target": "example.com"},
    )
    engine._tasks[task.id] = task
    await engine._execute_task(task)

    assert len(adapter_calls) == 1
    assert adapter_calls[0][0] == "t3mp3st"
    assert task.status == TaskStatus.COMPLETED
    assert task.result == {
        "module": "T3MP3ST",
        "category": "security",
        "url": "https://github.com/elder-plinius/T3MP3ST",
        "capabilities": [],
        "execution": {"status": "success", "source": "adapter"},
    }


@pytest.mark.asyncio
async def test_execute_task_uses_t3mp3st_adapter_with_uppercase_module_id(tmp_path, monkeypatch):
    config = AgencyConfig(
        data_dir=str(tmp_path),
        t3mp3st_approval_token="super-secret",
    )
    engine = AgencyEngine(config)

    module = RepoNode(
        id="T3MP3ST",
        name="T3MP3ST",
        owner="elder-plinius",
        full_name="elder-plinius/T3MP3ST",
        url="https://github.com/elder-plinius/T3MP3ST",
        category=RepoCategory.SECURITY,
    )
    engine.registry._modules["T3MP3ST"] = module

    adapter_calls: list[tuple[str, dict[str, Any]]] = []

    async def fake_adapter_run(self, mod, payload):
        adapter_calls.append((mod.id, payload))
        return {"status": "success", "source": "adapter"}

    monkeypatch.setattr(T3mp3stMcpAdapter, "run", fake_adapter_run)

    task = AgencyTask(
        id="task_test_T3MP3ST",
        intent="run T3MP3ST against example.com",
        module_id="T3MP3ST",
        payload={"target": "example.com"},
    )
    engine._tasks[task.id] = task
    await engine._execute_task(task)

    assert len(adapter_calls) == 1
    assert adapter_calls[0][0] == "T3MP3ST"
    assert task.status == TaskStatus.COMPLETED
    assert task.result == {
        "module": "T3MP3ST",
        "category": "security",
        "url": "https://github.com/elder-plinius/T3MP3ST",
        "capabilities": [],
        "execution": {"status": "success", "source": "adapter"},
    }


def test_resolve_ecosystem_target_propagates_owner_and_adapter_config(tmp_path):
    config = AgencyConfig(
        data_dir=str(tmp_path),
        routing_rules=[{"pattern": "t3mp3st", "target": "t3mp3st"}],
        ecosystem={
            "t3mp3st": {
                "repo": "T3MP3ST",
                "owner": "elder-plinius",
                "url": "https://github.com/elder-plinius/T3MP3ST",
                "role": "red-team meta-harness",
                "adapter_config": {"blocked_targets": ["10.0.0.0/8"]},
            },
        },
    )
    router = TaskRouter(RepoRegistry(data_dir=str(tmp_path)), MessageBus(), config=config)
    node = router._resolve_ecosystem_target("t3mp3st")
    assert node is not None
    assert node.owner == "elder-plinius"
    assert node.full_name == "elder-plinius/T3MP3ST"
    assert node.adapter_config == {"blocked_targets": ["10.0.0.0/8"]}


def test_resolve_ecosystem_target_merges_adapter_config_into_synced_node(tmp_path):
    config = AgencyConfig(
        data_dir=str(tmp_path),
        routing_rules=[{"pattern": "t3mp3st", "target": "t3mp3st"}],
        ecosystem={
            "t3mp3st": {
                "repo": "T3MP3ST",
                "owner": "elder-plinius",
                "url": "https://github.com/elder-plinius/T3MP3ST",
                "role": "red-team meta-harness",
                "adapter_config": {
                    "blocked_targets": ["10.0.0.0/8"],
                    "allow_local": False,
                },
            },
        },
    )
    registry = RepoRegistry(data_dir=str(tmp_path))
    registry._modules["T3MP3ST"] = RepoNode(
        id="t3mp3st",
        name="T3MP3ST",
        owner="elder-plinius",
        full_name="elder-plinius/T3MP3ST",
        url="https://github.com/elder-plinius/T3MP3ST",
        category=RepoCategory.SECURITY,
        adapter_config={"allow_local": True, "timeout": 30},
    )
    router = TaskRouter(registry, MessageBus(), config=config)
    node = router._resolve_ecosystem_target("t3mp3st")
    assert node is not None
    assert node.adapter_config == {
        "allow_local": False,
        "timeout": 30,
        "blocked_targets": ["10.0.0.0/8"],
    }
    # The original registry node should not be mutated.
    assert registry._modules["T3MP3ST"].adapter_config == {"allow_local": True, "timeout": 30}


def test_classify_repo_content_media():
    category = _classify_repo(
        "youtube-automation-agent",
        "Automated YouTube channel management",
        ["youtube", "content"],
    )
    assert category == RepoCategory.CONTENT_MEDIA


def test_classify_repo_knowledge():
    category = _classify_repo(
        "claude-obsidian",
        "Obsidian vault second brain",
        ["obsidian", "knowledge"],
    )
    assert category == RepoCategory.KNOWLEDGE


def test_classify_repo_career():
    category = _classify_repo(
        "career-ops",
        "AI-powered job search system",
        ["career", "resume"],
    )
    assert category == RepoCategory.CAREER


@pytest.mark.asyncio
async def test_worker_start_does_not_duplicate_bus_subscriptions(engine):
    """Starting the worker multiple times must not re-register the bus listener."""
    await engine.start_worker()
    try:
        initial_subscriber_count = len(engine.bus._handlers.get("*", []))
        assert initial_subscriber_count == 1
        # Stop and restart the worker.
        await engine.stop_worker()
        await engine.start_worker()
        assert len(engine.bus._handlers.get("*", [])) == initial_subscriber_count
    finally:
        await engine.stop_worker()


@pytest.mark.asyncio
async def test_worker_start_registers_single_health_check(engine):
    """Health checks must not be duplicated across worker restarts."""
    await engine.start_worker()
    try:
        initial_check_count = len(engine.metrics._health_checks)
        await engine.stop_worker()
        await engine.start_worker()
        assert len(engine.metrics._health_checks) == initial_check_count
    finally:
        await engine.stop_worker()


def test_classify_repo_agent_framework_relaymux_letta():
    category = _classify_repo(
        "relaymux",
        "Telegram remote control for tmux coding agents",
        ["agent", "telegram", "tmux"],
    )
    assert category == RepoCategory.AGENT_FRAMEWORK

    category = _classify_repo(
        "letta-code",
        "Stateful agents with persistent memory",
        ["letta", "memory", "stateful"],
    )
    assert category == RepoCategory.AGENT_FRAMEWORK


@pytest.fixture
def router_with_five_new_modules(tmp_path):
    config = AgencyConfig(
        data_dir=str(tmp_path),
        routing_rules=[
            {"pattern": "relaymux|telegram|tmux|remote.agent", "target": "relaymux"},
            {"pattern": "obsidian|second.brain|vault|wiki|notes", "target": "claude_obsidian"},
            {"pattern": "youtube|video|channel|content|media", "target": "youtube_agent"},
            {"pattern": "letta|persistent.memory|stateful.agent|local.agent", "target": "letta_code"},
            {"pattern": "job|career|apply|linkedin|cv|resume", "target": "career_ops"},
            {"pattern": "html|landing.page|landingpage|deck|magazine|report|social.post|generate.page|cinematic|html-anything", "target": "html_anything"},
        ],
        ecosystem={
            "relaymux": {
                "repo": "relaymux",
                "owner": "mupt-ai",
                "url": "https://github.com/mupt-ai/relaymux",
                "role": "Telegram remote control",
            },
            "claude_obsidian": {
                "repo": "claude-obsidian",
                "owner": "AgriciDaniel",
                "url": "https://github.com/AgriciDaniel/claude-obsidian",
                "role": "Obsidian second brain",
            },
            "youtube_agent": {
                "repo": "youtube-automation-agent",
                "owner": "darkzOGx",
                "url": "https://github.com/darkzOGx/youtube-automation-agent",
                "role": "YouTube automation",
            },
            "letta_code": {
                "repo": "letta-code",
                "owner": "letta-ai",
                "url": "https://github.com/letta-ai/letta-code",
                "role": "Stateful local agents",
            },
            "career_ops": {
                "repo": "career-ops",
                "owner": "santifer",
                "url": "https://github.com/santifer/career-ops",
                "role": "AI job search",
            },
            "html_anything": {
                "repo": "html-anything",
                "owner": "nexu-io",
                "url": "https://github.com/nexu-io/html-anything",
                "role": "AI HTML generator",
            },
        },
    )
    registry = RepoRegistry(data_dir=str(tmp_path))
    for key in ("relaymux", "claude_obsidian", "youtube_agent", "letta_code", "career_ops", "html_anything"):
        registry._modules[key] = RepoNode(
            id=key,
            name=key.replace("_", "-"),
            full_name=f"owner/{key.replace('_', '-')}",
            url=f"https://github.com/owner/{key.replace('_', '-')}",
        )
    return TaskRouter(registry, MessageBus(), config=config)


@pytest.mark.asyncio
async def test_router_resolves_html_anything_intent(router_with_five_new_modules):
    task = await router_with_five_new_modules.route("generate a landing page from this prompt")
    assert task.module_id == "html_anything"


@pytest.mark.asyncio
async def test_router_resolves_relaymux_intent(router_with_five_new_modules):
    task = await router_with_five_new_modules.route("launch a remote agent via telegram")
    assert task.module_id == "relaymux"


@pytest.mark.asyncio
async def test_router_resolves_obsidian_intent(router_with_five_new_modules):
    task = await router_with_five_new_modules.route("open my obsidian second brain vault")
    assert task.module_id == "claude_obsidian"


@pytest.mark.asyncio
async def test_router_resolves_youtube_intent(router_with_five_new_modules):
    task = await router_with_five_new_modules.route("automate my youtube channel")
    assert task.module_id == "youtube_agent"


@pytest.mark.asyncio
async def test_router_resolves_letta_intent(router_with_five_new_modules):
    task = await router_with_five_new_modules.route("run a stateful letta agent with memory")
    assert task.module_id == "letta_code"


@pytest.mark.asyncio
async def test_router_resolves_career_intent(router_with_five_new_modules):
    task = await router_with_five_new_modules.route("apply to jobs on linkedin")
    assert task.module_id == "career_ops"


@pytest.mark.asyncio
async def test_engine_uses_generic_adapter_for_unknown_module(config, fake_registry, monkeypatch):
    from sahiixx_agency.adapters.generic_adapter import GenericAdapter

    async def fake_generic_run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", "module": node.name, "command": payload.get("command")}

    monkeypatch.setattr(GenericAdapter, "run", fake_generic_run)

    engine = AgencyEngine(config)
    engine.registry = fake_registry
    engine.router.registry = fake_registry
    fake_registry.modules = [
        RepoNode(
            id="demo",
            name="demo",
            owner="test",
            full_name="test/demo",
            url="https://github.com/test/demo",
            category=RepoCategory.UNCATEGORIZED,
        ),
    ]
    await engine.start_worker()
    task = await engine.dispatch("run the demo repo", {"command": "echo hello"})
    await asyncio.sleep(0.2)
    assert task.status == TaskStatus.COMPLETED
    assert task.result["execution"]["status"] == "success"
    await engine.stop_worker()

