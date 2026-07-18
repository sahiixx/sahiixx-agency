"""Tests for the portfolio publisher adapter."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from sahiixx_agency.adapters.portfolio_publisher import MARKER, PortfolioPublisherAdapter

DATA_TS = """export interface Project { id: string }
export const projects: Project[] = [
  {
    id: "opa",
    index: "04",
  },
  // __OPA_PORTFOLIO_INSERT__
];
"""

MODULE = {
    "id": "postiz-app",
    "name": "postiz-app",
    "description": "Social media scheduling tool",
    "language": "TypeScript",
    "url": "https://github.com/sahiixx/postiz-app",
    "is_fork": False,
}

ENTRY_JSON = json.dumps({
    "name": "Postiz",
    "tagline": "Schedule everything, everywhere.",
    "description": "A social scheduling pipeline.",
    "longDescription": ["One.", "Two."],
    "problem": "Posting by hand does not scale.",
    "architecture": "Next.js · workers · Redis",
    "statusNote": "Running locally.",
    "highlights": ["Multi-channel", "Queue-based"],
    "role": "Architect & sole engineer",
    "status": "Shipped",
    "stack": ["TypeScript", "Next.js", "Redis"],
    "url": "https://github.com/sahiixx/postiz-app",
})


class FakeLLM:
    def __init__(self, content: str = ENTRY_JSON) -> None:
        self.content = content

    async def chat(self, messages, **kwargs):
        return SimpleNamespace(content=self.content)


class FakeNotifications:
    def __init__(self) -> None:
        self.sent: list[tuple] = []

    async def send(self, channel, title, body, **kwargs):
        self.sent.append((channel, title, body))


@pytest.fixture
def workspace(tmp_path):
    """Temp portfolio repo + registry, returns (repo_dir, settings)."""
    repo = tmp_path / "portfolio"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "data.ts").write_text(DATA_TS, encoding="utf-8")
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"modules": [MODULE]}), encoding="utf-8")
    settings = {
        "enabled": True,
        "dry_run": True,
        "repo_path": str(repo),
        "registry_path": str(registry),
        "ignore": [],
        "notify_channels": ["sse"],
    }
    return repo, settings


def make_adapter(settings, **overrides):
    return PortfolioPublisherAdapter(
        settings=settings,
        llm_manager=overrides.get("llm", FakeLLM()),
        notifications=overrides.get("notifications", FakeNotifications()),
        clone_base_dir=overrides.get("clone_base_dir", "/tmp"),
    )


@pytest.mark.asyncio
async def test_disabled_returns_skipped(workspace):
    repo, settings = workspace
    settings["enabled"] = False
    result = await make_adapter(settings).execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "skipped"
    assert "disabled" in result["reason"]


@pytest.mark.asyncio
async def test_no_module_match_fails_and_notifies(workspace):
    repo, settings = workspace
    notifications = FakeNotifications()
    adapter = make_adapter(settings, notifications=notifications)
    result = await adapter.execute({"brief": "publish portfolio entry for nonexistent"})
    assert result["status"] == "failed"
    assert len(notifications.sent) == 1


@pytest.mark.asyncio
async def test_gate_skips_fork(workspace):
    repo, settings = workspace
    registry = settings["registry_path"]
    forked = dict(MODULE, is_fork=True)
    with open(registry, "w", encoding="utf-8") as fh:
        json.dump({"modules": [forked]}, fh)
    result = await make_adapter(settings).execute({"brief": "publish portfolio entry for postiz-app"})
    assert result == {"status": "skipped", "reason": "fork", "module": "postiz-app"}


@pytest.mark.asyncio
async def test_gate_skips_already_published(workspace):
    repo, settings = workspace
    data_ts = repo / "src" / "data.ts"
    data_ts.write_text(DATA_TS.replace('id: "opa"', 'id: "postiz-app"'), encoding="utf-8")
    result = await make_adapter(settings).execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "skipped"
    assert result["reason"] == "already published"


@pytest.mark.asyncio
async def test_missing_marker_fails(workspace):
    repo, settings = workspace
    (repo / "src" / "data.ts").write_text(DATA_TS.replace(MARKER, "// nothing"), encoding="utf-8")
    result = await make_adapter(settings).execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "failed"
    assert "marker" in result["error"].lower()


@pytest.mark.asyncio
async def test_dry_run_renders_without_touching_disk(workspace, monkeypatch):
    repo, settings = workspace
    notifications = FakeNotifications()
    adapter = make_adapter(settings, notifications=notifications)

    async def fake_run(command, *, cwd, timeout):
        if command.startswith("git status"):
            return True, ""  # clean tree
        return True, "ok"

    monkeypatch.setattr(adapter, "_run", fake_run)
    data_ts = repo / "src" / "data.ts"
    before = data_ts.read_text(encoding="utf-8")
    result = await adapter.execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "success"
    assert result["dry_run"] is True
    assert 'id: "postiz-app"' in result["entry"]
    assert data_ts.read_text(encoding="utf-8") == before
    assert any("dry-run" in title.lower() for _, title, _ in notifications.sent)


@pytest.mark.asyncio
async def test_full_pipeline_inserts_builds_commits_deploys(workspace, monkeypatch):
    repo, settings = workspace
    settings["dry_run"] = False
    adapter = make_adapter(settings)
    calls: list[str] = []

    async def fake_run(command, *, cwd, timeout):
        calls.append(command)
        if command.startswith("git status"):
            return True, ""  # clean tree
        return True, "ok"

    monkeypatch.setattr(adapter, "_run", fake_run)
    result = await adapter.execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "success"
    assert result["deployed"] is True
    content = (repo / "src" / "data.ts").read_text(encoding="utf-8")
    assert 'id: "postiz-app"' in content
    assert content.index('id: "postiz-app"') < content.index(MARKER)
    assert '\n  {\n    id: "postiz-app",' in content
    assert any("npm run build" in c for c in calls)
    assert any("wrangler pages deploy dist" in c for c in calls)
    assert any("git commit" in c for c in calls)
    assert any(c == "git push" for c in calls)


@pytest.mark.asyncio
async def test_build_failure_restores_data_ts(workspace, monkeypatch):
    repo, settings = workspace
    settings["dry_run"] = False
    adapter = make_adapter(settings)
    data_ts = repo / "src" / "data.ts"
    original = data_ts.read_text(encoding="utf-8")

    async def fake_run(command, *, cwd, timeout):
        if command.startswith("git status"):
            return True, ""
        if command == "npm run build":
            return False, "TS error: boom"
        return True, "ok"

    monkeypatch.setattr(adapter, "_run", fake_run)
    result = await adapter.execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "failed"
    assert "build failed" in result["error"]
    assert data_ts.read_text(encoding="utf-8") == original


@pytest.mark.asyncio
async def test_dirty_repo_aborts_before_drafting(workspace, monkeypatch):
    repo, settings = workspace
    settings["dry_run"] = False
    llm = FakeLLM()
    adapter = make_adapter(settings, llm=llm)
    llm_called = []

    original_chat = llm.chat

    async def tracking_chat(messages, **kwargs):
        llm_called.append(True)
        return await original_chat(messages, **kwargs)

    llm.chat = tracking_chat

    async def fake_run(command, *, cwd, timeout):
        if command.startswith("git status"):
            return True, " M src/data.ts"
        return True, "ok"

    monkeypatch.setattr(adapter, "_run", fake_run)
    result = await adapter.execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "failed"
    assert "uncommitted" in result["error"]
    assert llm_called == []


@pytest.mark.asyncio
async def test_explicit_module_id_bypasses_fuzzy_match(workspace, monkeypatch):
    repo, settings = workspace
    adapter = make_adapter(settings)

    async def fake_run(command, *, cwd, timeout):
        return True, ""

    monkeypatch.setattr(adapter, "_run", fake_run)
    result = await adapter.execute({"brief": "unrelated text", "module_id": "postiz-app"})
    assert result["status"] == "success"
    assert result["module"] == "postiz-app"


@pytest.mark.asyncio
async def test_explicit_module_id_not_found(workspace):
    repo, settings = workspace
    notifications = FakeNotifications()
    adapter = make_adapter(settings, notifications=notifications)
    result = await adapter.execute({"brief": "x", "module_id": "ghost-module"})
    assert result["status"] == "failed"
    assert "not found in registry" in result["error"]
    assert len(notifications.sent) == 1


@pytest.mark.asyncio
async def test_registry_unreadable_fails(workspace):
    repo, settings = workspace
    settings["registry_path"] = str(repo / "missing.json")
    result = await make_adapter(settings).execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "failed"
    assert "registry unreadable" in result["error"]


@pytest.mark.asyncio
async def test_unreadable_data_ts_fails_and_notifies(workspace):
    repo, settings = workspace
    settings["repo_path"] = str(repo / "nonexistent")
    notifications = FakeNotifications()
    adapter = make_adapter(settings, notifications=notifications)
    result = await adapter.execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "failed"
    assert "data.ts not readable" in result["error"]
    assert len(notifications.sent) == 1


@pytest.mark.asyncio
async def test_commit_failure_unstages_and_restores(workspace, monkeypatch):
    repo, settings = workspace
    settings["dry_run"] = False
    adapter = make_adapter(settings)
    data_ts = repo / "src" / "data.ts"
    original = data_ts.read_text(encoding="utf-8")
    calls: list[str] = []

    async def fake_run(command, *, cwd, timeout):
        calls.append(command)
        if command.startswith("git status"):
            return True, ""
        if command.startswith("git commit"):
            return False, "nothing to commit"
        return True, "ok"

    monkeypatch.setattr(adapter, "_run", fake_run)
    result = await adapter.execute({"brief": "publish portfolio entry for postiz-app"})
    assert result["status"] == "failed"
    assert "git commit failed" in result["error"]
    assert "git restore --staged src/data.ts" in calls
    assert data_ts.read_text(encoding="utf-8") == original
