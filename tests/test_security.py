"""Tests for the security hardening layer."""

from __future__ import annotations

import pytest

from sahiixx_agency.core.memory import AgencyMemory
from sahiixx_agency.core.security import (
    AuditLogger,
    InputSanitizer,
    NetworkPolicy,
    SecretsManager,
    SecretValue,
)


def test_secret_value_masks() -> None:
    s = SecretValue("sk-1234567890abcdef", "api_key")
    assert s.value == "sk-1234567890abcdef"
    assert "sk-12" not in str(s)
    assert "..." in str(s)


def test_secrets_manager_prefers_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "gh_env_token")
    sm = SecretsManager()
    secret = sm.register("github_token", env_var="GITHUB_TOKEN", config_value="gh_config_token")
    assert secret.value == "gh_env_token"


def test_secrets_manager_falls_back_to_config() -> None:
    sm = SecretsManager()
    secret = sm.register("github_token", env_var="GITHUB_TOKEN", config_value="gh_config_token")
    assert secret.value == "gh_config_token"


def test_secrets_manager_rejects_placeholders() -> None:
    sm = SecretsManager()
    with pytest.raises(ValueError):
        sm.register("github_token", config_value="YOUR_GITHUB_TOKEN_HERE")
    with pytest.raises(ValueError):
        sm.register("api_key", config_value="sk-example")
    with pytest.raises(ValueError):
        sm.register("token", config_value="token")


def test_secrets_manager_masks_text() -> None:
    sm = SecretsManager()
    sm.register("github_token", config_value="gh_secret_value")
    masked = sm.mask("Error: gh_secret_value leaked")
    assert "gh_secret_value" not in masked
    assert "..." in masked
    assert masked == "Error: gh_s...alue leaked"


def test_audit_logger_stores_events(tmp_path: pytest.TempPathFactory) -> None:
    memory = AgencyMemory(data_dir=str(tmp_path), backend="json")
    logger = AuditLogger(memory)
    logger.log("task.dispatched", "operator", "task_123", {"intent": "test"})
    events = memory.recent_events(topic="audit")
    assert len(events) == 1
    assert events[0]["payload"]["action"] == "task.dispatched"


def test_input_sanitizer_strips_control_chars() -> None:
    clean = InputSanitizer.sanitize_intent("hello\x00world")
    assert "\x00" not in clean


def test_input_sanitizer_rejects_shell_metachars() -> None:
    with pytest.raises(ValueError):
        InputSanitizer.sanitize_intent("run; rm -rf /")
    with pytest.raises(ValueError):
        InputSanitizer.sanitize_intent("run | cat")


def test_input_sanitizer_rejects_long_intent() -> None:
    with pytest.raises(ValueError):
        InputSanitizer.sanitize_intent("x" * 5000)


def test_input_sanitizer_sanitizes_payload() -> None:
    payload = {"name": "ok", "bad": "has\x01control", "nested": {"x": "\x02"}}
    clean = InputSanitizer.sanitize_payload(payload)
    assert clean["bad"] == "hascontrol"
    assert clean["nested"]["x"] == ""


def test_network_policy_allowlist() -> None:
    policy = NetworkPolicy(allowlist=["github.com", "api.openai.com"])
    assert policy.is_allowed("api.github.com")
    assert policy.is_allowed("api.openai.com")
    assert not policy.is_allowed("evil.com")


def test_network_policy_blocklist() -> None:
    policy = NetworkPolicy(blocklist=["evil.com"])
    assert not policy.is_allowed("evil.com")
    assert policy.is_allowed("github.com")


def test_network_policy_default_deny() -> None:
    policy = NetworkPolicy(allowlist=["github.com"], default_allow=False)
    assert policy.is_allowed("github.com")
    assert not policy.is_allowed("example.com")
