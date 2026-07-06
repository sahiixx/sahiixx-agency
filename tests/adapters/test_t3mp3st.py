"""Tests for the T3MP3ST security adapter."""

from __future__ import annotations

import pytest

from sahiixx_agency.adapters.security._t3mp3st_validation import validate_target
from sahiixx_agency.adapters.security.t3mp3st import T3mp3stAdapter
from sahiixx_agency.core.models import RepoNode


def test_validate_target_accepts_public_host():
    assert validate_target("example.com") is None


def test_validate_target_rejects_localhost():
    assert validate_target("localhost") == "blocked_target"


def test_validate_target_rejects_private_ip():
    assert validate_target("192.168.1.1") == "blocked_target"


def test_validate_target_allows_local_when_configured():
    assert validate_target("localhost", allow_local=True) is None


def test_validate_target_rejects_empty():
    assert validate_target("") == "missing_target"


def test_validate_target_accepts_url():
    assert validate_target("https://example.com/path") is None


@pytest.fixture
def t3mp3st_module(tmp_path):
    return RepoNode(
        id="T3MP3ST",
        name="T3MP3ST",
        full_name="elder-plinius/T3MP3ST",
        url="https://github.com/elder-plinius/T3MP3ST",
        clone_url="https://github.com/elder-plinius/T3MP3ST.git",
    )


@pytest.mark.asyncio
async def test_t3mp3st_adapter_rejects_missing_target(t3mp3st_module):
    adapter = T3mp3stAdapter(approval_token="secret")
    result = await adapter.run(t3mp3st_module, {})
    assert result["status"] == "validation_error"
    assert result["error_code"] == "missing_target"


@pytest.mark.asyncio
async def test_t3mp3st_adapter_rejects_localhost(t3mp3st_module):
    adapter = T3mp3stAdapter(approval_token="secret")
    result = await adapter.run(t3mp3st_module, {"target": "localhost"})
    assert result["status"] == "validation_error"
    assert result["error_code"] == "blocked_target"


@pytest.mark.asyncio
async def test_t3mp3st_adapter_requires_approval_for_full(t3mp3st_module):
    adapter = T3mp3stAdapter(approval_token="secret")
    result = await adapter.run(t3mp3st_module, {"target": "example.com", "mode": "full"})
    assert result["status"] == "validation_error"
    assert result["error_code"] == "approval_required"


@pytest.mark.asyncio
async def test_t3mp3st_adapter_accepts_full_with_valid_approval(t3mp3st_module, monkeypatch):
    adapter = T3mp3stAdapter(approval_token="secret")
    captured = {}

    async def fake_super_run(self, module, payload):
        captured["env"] = payload.get("env")
        captured["module"] = module.name
        return {"status": "success", "module": module.name}

    monkeypatch.setattr("sahiixx_agency.adapters.base.BaseAdapter.run", fake_super_run)
    result = await adapter.run(
        t3mp3st_module,
        {"target": "example.com", "mode": "full", "approval": "secret"},
    )
    assert result["status"] == "success"
    assert captured["env"]["T3MP3ST_FULL_ARSENAL"] == "1"
    assert captured["env"]["T3MP3ST_TARGET"] == "example.com"


@pytest.mark.asyncio
async def test_t3mp3st_adapter_defaults_to_lite(t3mp3st_module, monkeypatch):
    adapter = T3mp3stAdapter()
    captured = {}

    async def fake_super_run(self, module, payload):
        captured["env"] = payload.get("env")
        return {"status": "success", "module": module.name}

    monkeypatch.setattr("sahiixx_agency.adapters.base.BaseAdapter.run", fake_super_run)
    result = await adapter.run(t3mp3st_module, {"target": "example.com"})
    assert result["status"] == "success"
    assert captured["env"]["T3MP3ST_FULL_ARSENAL"] == "0"


def test_validate_payload_returns_env_and_error(t3mp3st_module):
    adapter = T3mp3stAdapter(approval_token="secret")
    env, error = adapter._validate_payload(
        {"target": "example.com", "mode": "full", "approval": "secret"}
    )
    assert error is None
    assert env["T3MP3ST_TARGET"] == "example.com"
    assert env["T3MP3ST_FULL_ARSENAL"] == "1"


def test_validate_payload_returns_error_for_blocked_target(t3mp3st_module):
    adapter = T3mp3stAdapter()
    env, error = adapter._validate_payload({"target": "localhost"})
    assert env is None
    assert error["error_code"] == "blocked_target"


def test_validate_payload_rejects_invalid_mode():
    adapter = T3mp3stAdapter(approval_token="secret")
    env, error = adapter._validate_payload({"target": "example.com", "mode": "nuclear"})
    assert env is None
    assert error["error_code"] == "invalid_mode"


def test_validate_payload_approval_mismatch():
    adapter = T3mp3stAdapter(approval_token="secret")
    env, error = adapter._validate_payload(
        {"target": "example.com", "mode": "full", "approval": "wrong"}
    )
    assert env is None
    assert error["error_code"] == "approval_mismatch"


def test_validate_payload_approval_not_configured():
    adapter = T3mp3stAdapter()
    env, error = adapter._validate_payload({"target": "example.com", "mode": "full"})
    assert env is None
    assert error["error_code"] == "approval_not_configured"


def test_validate_target_rejects_invalid_hostname():
    assert validate_target("not a valid host!!!") == "invalid_target"


def test_validate_payload_uses_custom_blocked_networks(t3mp3st_module):
    adapter = T3mp3stAdapter()
    module = t3mp3st_module.model_copy(
        update={"adapter_config": {"blocked_targets": ["8.8.8.8/32"]}}
    )
    env, error = adapter._validate_payload(
        {"target": "8.8.8.8"},
        blocked_networks=module.adapter_config.get("blocked_targets"),
    )
    assert env is None
    assert error["error_code"] == "blocked_target"
