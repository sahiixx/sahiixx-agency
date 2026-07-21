"""Security hardening for the One Person Agency.

Provides centralized secret management, audit logging, input sanitization,
and a network egress policy stub for sandboxed execution.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any

from sahiixx_agency.core.memory import AgencyMemory


class SecretValue:
    """Wrapper that masks a secret in repr/str but allows code to read it."""

    def __init__(self, value: str | None, name: str) -> None:
        self._value = value
        self.name = name

    @property
    def value(self) -> str | None:
        return self._value

    def __bool__(self) -> bool:
        return bool(self._value)

    def __str__(self) -> str:
        return self._mask()

    def __repr__(self) -> str:
        return f"SecretValue({self.name}={self._mask()})"

    def _mask(self) -> str:
        if not self._value:
            return "<not set>"
        if len(self._value) <= 8:
            return "***"
        return f"{self._value[:4]}...{self._value[-4:]}"


class SecretsManager:
    """Load and guard secrets from environment variables.

    Refuses values that look like literal placeholders (e.g. 'YOUR_TOKEN_HERE')
    and warns when a secret is read from config instead of the environment.
    """

    # Patterns that suggest a hardcoded placeholder rather than a real secret.
    _PLACEHOLDER_PATTERNS = [
        re.compile(r"^YOUR_[A-Z_]+_HERE$"),
        re.compile(r"^REPLACE_WITH_"),
        re.compile(r"^sk-(example|placeholder|test)"),
        re.compile(r"^(token|key|secret|password|pwd)$", re.IGNORECASE),
        re.compile(r"^\*+$"),
    ]

    def __init__(self) -> None:
        self._secrets: dict[str, SecretValue] = {}

    def register(
        self,
        name: str,
        env_var: str | None = None,
        config_value: str | None = None,
        required: bool = False,
    ) -> SecretValue:
        """Register a secret, preferring environment over config."""
        env_var = env_var or name
        raw = os.environ.get(env_var) if env_var else None
        if raw is None and config_value is not None:
            raw = config_value

        if raw is not None and self._looks_like_placeholder(raw):
            raise ValueError(
                f"Secret {name} appears to be a placeholder ({raw!r}). "
                f"Set {env_var} in the environment instead."
            )

        secret = SecretValue(raw, name)
        self._secrets[name] = secret
        if required and not secret:
            raise RuntimeError(f"Required secret {name} is not set (env var: {env_var})")
        return secret

    def get(self, name: str) -> SecretValue | None:
        return self._secrets.get(name)

    def get_value(self, name: str) -> str | None:
        secret = self._secrets.get(name)
        return secret.value if secret else None

    def mask(self, text: str) -> str:
        """Mask all known secret values inside a string."""
        for secret in self._secrets.values():
            if secret.value:
                text = text.replace(secret.value, str(secret))
        return text

    @classmethod
    def _looks_like_placeholder(cls, value: str) -> bool:
        return any(pattern.match(value) for pattern in cls._PLACEHOLDER_PATTERNS)


class AuditLogger:
    """Append-only audit log backed by AgencyMemory events."""

    def __init__(self, memory: AgencyMemory | None = None) -> None:
        self.memory = memory

    def log(
        self,
        action: str,
        actor: str,
        target_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record a security-relevant event."""
        payload = {
            "action": action,
            "actor": actor,
            "target_id": target_id,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if self.memory is not None:
            self.memory.log_event("audit", payload)


class InputSanitizer:
    """Sanitize user-provided intents and payloads."""

    MAX_INTENT_LENGTH = 4000
    _CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
    _SHELL_METACHARS = re.compile(r"[;&|`$(){}[\]\\<>]")

    @classmethod
    def sanitize_intent(cls, intent: str) -> str:
        if not isinstance(intent, str):
            raise ValueError("Intent must be a string")
        intent = intent.strip()
        if len(intent) > cls.MAX_INTENT_LENGTH:
            raise ValueError(f"Intent exceeds max length of {cls.MAX_INTENT_LENGTH}")
        intent = cls._CONTROL_CHARS.sub("", intent)
        # Block obvious shell injection attempts.
        if cls._SHELL_METACHARS.search(intent):
            raise ValueError("Intent contains disallowed characters")
        return intent

    @classmethod
    def sanitize_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        """Recursively strip control characters from string payload values."""
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a dict")
        return {k: cls._sanitize_value(v) for k, v in payload.items()}

    @classmethod
    def _sanitize_value(cls, value: Any) -> Any:
        if isinstance(value, str):
            return cls._CONTROL_CHARS.sub("", value)
        if isinstance(value, list):
            return [cls._sanitize_value(v) for v in value]
        if isinstance(value, dict):
            return {k: cls._sanitize_value(v) for k, v in value.items()}
        return value


class NetworkPolicy:
    """Stub for sandboxed execution network egress controls.

    A real implementation would integrate with the runner to enforce
    allowlists/blocklists at the process/network level.
    """

    def __init__(
        self,
        allowlist: list[str] | None = None,
        blocklist: list[str] | None = None,
        default_allow: bool = True,
    ) -> None:
        self.allowlist = set(allowlist or [])
        self.blocklist = set(blocklist or [])
        self.default_allow = default_allow

    def is_allowed(self, host: str) -> bool:
        """Proper domain boundary matching to prevent bypass.

        A naive endswith() check lets 'evil.com' match 'notevil.com'
        or 'myevil.com'. Require an exact match or a proper
        '.domain' suffix so only true subdomains are caught.
        """
        host = host.lower().rstrip(".")
        if self.blocklist:
            for domain in self.blocklist:
                domain = domain.lower().rstrip(".")
                if host == domain or host.endswith("." + domain):
                    return False
        if self.allowlist:
            for domain in self.allowlist:
                domain = domain.lower().rstrip(".")
                if host == domain or host.endswith("." + domain):
                    return True
            return False
        return self.default_allow

    @property
    def allow_all(self) -> bool:
        """Return True when the policy imposes no host restrictions."""
        return self.default_allow and not self.allowlist and not self.blocklist
