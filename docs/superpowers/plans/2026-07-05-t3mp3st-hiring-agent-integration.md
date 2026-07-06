# T3MP3ST + Hiring-Agent Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Register `elder-plinius/T3MP3ST` and `interviewstreet/hiring-agent` in OPA, harden T3MP3ST execution with target scoping and arsenal gating, and add an MCP-native invocation path with subprocess fallback.

**Architecture:** Extend OPA's existing `SecurityAdapter` with a dedicated `T3mp3stAdapter` that validates payloads and injects safety environment variables; add a thin `T3mp3stMcpAdapter` that talks to T3MP3ST's MCP server over stdio and falls back to the subprocess adapter; register both modules plus new routing rules in `config/agency.yaml`.

**Tech Stack:** Python 3.12, Pydantic v2, `mcp` Python SDK, PyYAML, pytest, pytest-asyncio.

## Global Constraints

- Target Python 3.10+ syntax; use `from __future__ import annotations` in all new files.
- Line length 120 (ruff default in project).
- Type-hint everything.
- No live network calls in tests.
- No real T3MP3ST tools executed during tests.
- Approval token comparison must use constant-time `hmac.compare_digest`.
- Local/private network targets are blocked by default for T3MP3ST.

## File Structure

| File | Responsibility |
|------|----------------|
| `sahiixx_agency/adapters/security/_t3mp3st_validation.py` | Target host/IP/URL validation and block-list checks. |
| `sahiixx_agency/adapters/security/t3mp3st.py` | Payload validation, safety env injection, subprocess execution for T3MP3ST. |
| `sahiixx_agency/adapters/security/t3mp3st_mcp.py` | MCP client wrapper around T3MP3ST with auto-discovery and subprocess fallback. |
| `sahiixx_agency/adapters/security/__init__.py` | Export `SecurityAdapter`, `T3mp3stAdapter`, `T3mp3stMcpAdapter`. |
| `sahiixx_agency/core/models.py` | Add `t3mp3st_approval_token` to `AgencyConfig`. |
| `sahiixx_agency/cli/main.py` | Merge `T3MP3ST_APPROVAL_TOKEN` env var into config load. |
| `config/agency.yaml` | Add `t3mp3st` and `hiring_agent` ecosystem entries + routing rules. |
| `tests/adapters/test_t3mp3st.py` | Unit tests for validation, safety gates, subprocess path. |
| `tests/adapters/test_t3mp3st_mcp.py` | Unit tests for MCP adapter fallback. |
| `tests/test_core.py` | Tests for routing rules and config token loading. |

---

### Task 1: Add `t3mp3st_approval_token` to `AgencyConfig`

**Files:**
- Modify: `sahiixx_agency/core/models.py:128-152`
- Modify: `sahiixx_agency/cli/main.py:39-50`
- Test: `tests/test_core.py`

**Interfaces:**
- Consumes: existing `AgencyConfig` fields.
- Produces: `AgencyConfig.t3mp3st_approval_token: str | None`, env var `T3MP3ST_APPROVAL_TOKEN` loaded into config.

- [ ] **Step 1: Write the failing test for config token loading**

Append to `tests/test_core.py`:

```python
from sahiixx_agency.core.models import AgencyConfig


def test_agency_config_loads_t3mp3st_approval_token():
    config = AgencyConfig(t3mp3st_approval_token="super-secret")
    assert config.t3mp3st_approval_token == "super-secret"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd /c/Users/sahii/sahiixx-agency
pytest tests/test_core.py::test_agency_config_loads_t3mp3st_approval_token -v
```

Expected: `FAIL` with `unexpected keyword argument` or field validation error.

- [ ] **Step 3: Add the field to `AgencyConfig`**

Modify `sahiixx_agency/core/models.py` inside `AgencyConfig`, after `llm_api_key` and before `routing_rules`:

```python
    t3mp3st_approval_token: str | None = Field(
        default=None,
        description="Token required to authorize T3MP3ST full-arsenal mode.",
    )
```

- [ ] **Step 4: Load the token from environment in CLI config loader**

Modify `sahiixx_agency/cli/main.py` in `_load_config()`:

```python
def _load_config() -> AgencyConfig:
    config_path = os.environ.get("OPA_CONFIG", "./config/agency.yaml")
    if os.path.exists(config_path):
        import yaml

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        data.setdefault("t3mp3st_approval_token", os.environ.get("T3MP3ST_APPROVAL_TOKEN"))
        return AgencyConfig.model_validate(data)
    return AgencyConfig(
        github_token=os.environ.get("GITHUB_TOKEN"),
        github_username=os.environ.get("GITHUB_USER", "sahiixx"),
        t3mp3st_approval_token=os.environ.get("T3MP3ST_APPROVAL_TOKEN"),
    )
```

- [ ] **Step 5: Run the test to verify it passes**

Run:

```bash
pytest tests/test_core.py::test_agency_config_loads_t3mp3st_approval_token -v
```

Expected: `PASS`.

- [ ] **Step 6: Commit**

```bash
git add sahiixx_agency/core/models.py sahiixx_agency/cli/main.py tests/test_core.py
git commit -m "feat(config): add T3MP3ST_APPROVAL_TOKEN support"
```

---

### Task 2: Create T3MP3ST target validation utility

**Files:**
- Create: `sahiixx_agency/adapters/security/_t3mp3st_validation.py`
- Test: `tests/adapters/test_t3mp3st.py`

**Interfaces:**
- Consumes: target string, `allow_local` flag, block-list config.
- Produces: `validate_target(target: str, *, allow_local: bool = False, blocked_networks: list[str] | None = None) -> str | None` returning an error code or `None`.

- [ ] **Step 1: Write the failing tests**

Create `tests/adapters/test_t3mp3st.py`:

```python
"""Tests for the T3MP3ST security adapter."""

from __future__ import annotations

import pytest

from sahiixx_agency.adapters.security._t3mp3st_validation import validate_target


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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/adapters/test_t3mp3st.py -v
```

Expected: `ModuleNotFoundError` or import errors.

- [ ] **Step 3: Implement the validation utility**

Create `sahiixx_agency/adapters/security/_t3mp3st_validation.py`:

```python
"""Validation helpers for T3MP3ST target scoping."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
_DEFAULT_BLOCKED_NETWORKS = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "fc00::/7",
]


def _host_from_target(target: str) -> str:
    """Extract a hostname from a target that may be a URL, IP, or plain host."""
    stripped = target.strip()
    if "//" not in stripped:
        stripped = f"//{stripped}"
    parsed = urlparse(stripped)
    host = parsed.hostname or stripped.lstrip("/")
    return host.lower()


def _is_blocked_host(host: str, allow_local: bool) -> bool:
    if allow_local:
        return False
    return host in _BLOCKED_HOSTS


def _is_blocked_network(host: str, networks: list[str], allow_local: bool) -> bool:
    if allow_local:
        return False
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    for net_str in networks:
        network = ipaddress.ip_network(net_str, strict=False)
        if addr in network:
            return True
    return False


def validate_target(
    target: str,
    *,
    allow_local: bool = False,
    blocked_networks: list[str] | None = None,
) -> str | None:
    """Validate a T3MP3ST target.

    Returns an error code string or ``None`` if the target is acceptable.
    """
    if not target or not target.strip():
        return "missing_target"

    host = _host_from_target(target)
    if not host:
        return "invalid_target"

    if _is_blocked_host(host, allow_local):
        return "blocked_target"

    networks = blocked_networks or _DEFAULT_BLOCKED_NETWORKS
    if _is_blocked_network(host, networks, allow_local):
        return "blocked_target"

    return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run:

```bash
pytest tests/adapters/test_t3mp3st.py -v
```

Expected: all `PASS`.

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/adapters/security/_t3mp3st_validation.py tests/adapters/test_t3mp3st.py
git commit -m "feat(security): add T3MP3ST target validation"
```

---

### Task 3: Create `T3mp3stAdapter` (subprocess path)

**Files:**
- Create: `sahiixx_agency/adapters/security/t3mp3st.py`
- Modify: `sahiixx_agency/adapters/security/__init__.py`
- Test: `tests/adapters/test_t3mp3st.py`

**Interfaces:**
- Consumes: `RepoNode`, payload dict, `t3mp3st_approval_token`.
- Produces: `T3mp3stAdapter` with async `run(module, payload) -> dict[str, Any]`, plus `_validate_payload(payload)` returning `(env, error)` for reuse by the MCP adapter.

- [ ] **Step 1: Write the failing tests**

Append to `tests/adapters/test_t3mp3st.py`:

```python
import pytest

from sahiixx_agency.adapters.security.t3mp3st import T3mp3stAdapter
from sahiixx_agency.core.models import RepoNode


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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/adapters/test_t3mp3st.py -v
```

Expected: import / missing class errors.

- [ ] **Step 3: Implement `T3mp3stAdapter`**

Create `sahiixx_agency/adapters/security/t3mp3st.py`:

```python
"""Safety-hardened adapter for the T3MP3ST red-team framework."""

from __future__ import annotations

import hmac
from typing import Any

from sahiixx_agency.adapters.base import BaseAdapter
from sahiixx_agency.adapters.security._t3mp3st_validation import validate_target
from sahiixx_agency.core.models import RepoNode


class T3mp3stAdapter(BaseAdapter):
    """Adapter for T3MP3ST with target scoping and arsenal gating."""

    def __init__(
        self,
        clone_base_dir: str = "./data/repos",
        approval_token: str | None = None,
    ) -> None:
        super().__init__(clone_base_dir=clone_base_dir)
        self.approval_token = approval_token

    def _validate_payload(
        self,
        payload: dict[str, Any],
    ) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
        """Validate payload and build the safety environment dict.

        Returns ``(env, error)``. ``env`` is ``None`` when validation fails.
        """
        target = payload.get("target")
        mode = payload.get("mode", "lite")
        approval = payload.get("approval")
        allow_local = payload.get("allow_local", False)

        if mode not in {"lite", "full"}:
            return None, {
                "status": "validation_error",
                "error_code": "invalid_mode",
                "message": "mode must be 'lite' or 'full'",
            }

        error = validate_target(target, allow_local=allow_local)
        if error:
            return None, {
                "status": "validation_error",
                "error_code": error,
                "message": f"Target '{target}' failed validation: {error}",
            }

        full_arsenal = "0"
        if mode == "full":
            if not self.approval_token:
                return None, {
                    "status": "validation_error",
                    "error_code": "approval_not_configured",
                    "message": "Full arsenal requested but no approval token is configured in OPA.",
                }
            if not approval or not hmac.compare_digest(approval, self.approval_token):
                return None, {
                    "status": "validation_error",
                    "error_code": "approval_mismatch",
                    "message": "Full arsenal requested but approval token is missing or invalid.",
                }
            full_arsenal = "1"

        env: dict[str, str] = {
            "T3MP3ST_TARGET": target,
            "T3MP3ST_FULL_ARSENAL": full_arsenal,
            "T3MP3ST_EGRESS_POLICY": "scoped",
        }
        return env, None

    async def run(self, module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        env, error = self._validate_payload(payload)
        if error:
            return error

        run_payload = {
            **payload,
            "env": env,
            "timeout": payload.get("timeout", 180),
        }
        result = await super().run(module, run_payload)
        result["t3mp3st_mode"] = payload.get("mode", "lite")
        result["t3mp3st_target"] = payload["target"]
        return result
```

- [ ] **Step 4: Export from security package**

Modify `sahiixx_agency/adapters/security/__init__.py`:

```python
"""Security adapters."""

from sahiixx_agency.adapters.security.runner import SecurityAdapter, run_security_module
from sahiixx_agency.adapters.security.t3mp3st import T3mp3stAdapter

__all__ = ["SecurityAdapter", "T3mp3stAdapter", "run_security_module"]
```

- [ ] **Step 5: Run the tests to verify they pass**

Run:

```bash
pytest tests/adapters/test_t3mp3st.py -v
```

Expected: all `PASS`.

- [ ] **Step 6: Commit**

```bash
git add sahiixx_agency/adapters/security/t3mp3st.py sahiixx_agency/adapters/security/__init__.py tests/adapters/test_t3mp3st.py
git commit -m "feat(security): add T3MP3ST safety-hardened subprocess adapter"
```


---

### Task 4: Create `T3mp3stMcpAdapter` (MCP path with fallback)

**Files:**
- Create: `sahiixx_agency/adapters/security/t3mp3st_mcp.py`
- Modify: `sahiixx_agency/adapters/security/__init__.py`
- Test: `tests/adapters/test_t3mp3st_mcp.py`

**Interfaces:**
- Consumes: `RepoNode`, payload dict, optional `tool_name` hint.
- Produces: `T3mp3stMcpAdapter` with async `run(module, payload) -> dict[str, Any]`; falls back to `T3mp3stAdapter` subprocess execution.

- [ ] **Step 1: Write the failing tests**

Create `tests/adapters/test_t3mp3st_mcp.py`:

```python
"""Tests for the T3MP3ST MCP adapter."""

from __future__ import annotations

import pytest

from sahiixx_agency.adapters.security.t3mp3st_mcp import T3mp3stMcpAdapter
from sahiixx_agency.core.models import RepoNode


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
async def test_mcp_adapter_falls_back_when_server_unavailable(t3mp3st_module, monkeypatch):
    adapter = T3mp3stMcpAdapter(approval_token="secret")

    async def fake_subprocess_run(self, module, payload):
        return {"status": "success", "source": "subprocess", "module": module.name}

    monkeypatch.setattr("sahiixx_agency.adapters.base.BaseAdapter.run", fake_subprocess_run)

    result = await adapter.run(t3mp3st_module, {"target": "example.com"})
    assert result["status"] == "success"
    assert result["source"] == "subprocess"
    assert result["fallback_reason"] == "mcp_server_not_found"


@pytest.mark.asyncio
async def test_mcp_adapter_reuses_validation_before_fallback(t3mp3st_module, monkeypatch):
    adapter = T3mp3stMcpAdapter()
    result = await adapter.run(t3mp3st_module, {"target": "localhost"})
    assert result["status"] == "validation_error"
    assert result["error_code"] == "blocked_target"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/adapters/test_t3mp3st_mcp.py -v
```

Expected: import error.

- [ ] **Step 3: Implement `T3mp3stMcpAdapter`**

Create `sahiixx_agency/adapters/security/t3mp3st_mcp.py`:

```python
"""MCP-native adapter for T3MP3ST with subprocess fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from sahiixx_agency.adapters.security.t3mp3st import T3mp3stAdapter
from sahiixx_agency.core.models import RepoNode

try:
    from mcp import ClientSession, StdioServerParameters, stdio_client
except ImportError:  # pragma: no cover - fallback if mcp not installed
    ClientSession = None  # type: ignore[misc, assignment]
    StdioServerParameters = None  # type: ignore[misc, assignment]
    stdio_client = None  # type: ignore[misc, assignment]


class T3mp3stMcpAdapter(T3mp3stAdapter):
    """Adapter that invokes T3MP3ST via MCP, falling back to subprocess."""

    def __init__(
        self,
        clone_base_dir: str = "./data/repos",
        approval_token: str | None = None,
        tool_name: str | None = None,
    ) -> None:
        super().__init__(clone_base_dir=clone_base_dir, approval_token=approval_token)
        self.tool_name = tool_name

    def _find_mcp_server_script(self, repo_path: Path) -> list[str] | None:
        """Discover the MCP server entrypoint inside the cloned repo."""
        package_json = repo_path / "package.json"
        if package_json.exists():
            with open(package_json, encoding="utf-8") as f:
                pkg = json.load(f)
            bin_field = pkg.get("bin")
            if isinstance(bin_field, dict):
                for name, rel_path in bin_field.items():
                    if "mcp" in name.lower() or "server" in name.lower():
                        return ["node", str(repo_path / rel_path)]
            if isinstance(bin_field, str):
                return ["node", str(repo_path / bin_field)]

        for candidate in [
            "dist/mcp-server.js",
            "build/mcp-server.js",
            "lib/mcp-server.js",
            "mcp-server.js",
            "dist/index.js",
            "build/index.js",
        ]:
            path = repo_path / candidate
            if path.exists():
                return ["node", str(path)]
        return None

    def _pick_tool(self, tools: list[dict[str, Any]]) -> str | None:
        if self.tool_name:
            return self.tool_name
        names = [t.get("name", "").lower() for t in tools]
        for name in names:
            if "recon" in name:
                return name
        for name in names:
            if "security" in name or "scan" in name:
                return name
        return names[0] if names else None

    async def run(self, module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        env, error = self._validate_payload(payload)
        if error:
            return error

        if stdio_client is None or ClientSession is None or StdioServerParameters is None:
            return await self._fallback(module, payload, reason="mcp_sdk_unavailable")

        try:
            path = await self.runner.clone_manager.clone(module)
        except Exception as exc:
            return await self._fallback(module, payload, reason="clone_failed", error=str(exc))

        server_cmd = self._find_mcp_server_script(path)
        if server_cmd is None:
            return await self._fallback(module, payload, reason="mcp_server_not_found")

        run_env = {**os.environ, **env}
        params = StdioServerParameters(
            command=server_cmd[0],
            args=server_cmd[1:],
            env=run_env,
        )

        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    tools = [
                        t.model_dump() if hasattr(t, "model_dump") else dict(t)
                        for t in tools_result.tools
                    ]
                    tool_name = self._pick_tool(tools)
                    if tool_name is None:
                        return await self._fallback(module, payload, reason="no_matching_mcp_tool")

                    result = await session.call_tool(
                        tool_name,
                        arguments={
                            "target": payload["target"],
                            "mode": payload.get("mode", "lite"),
                            "approval": payload.get("approval"),
                        },
                    )
                    return {
                        "status": "success",
                        "source": "mcp",
                        "tool": tool_name,
                        "result": result.model_dump() if hasattr(result, "model_dump") else dict(result),
                    }
        except Exception as exc:
            return await self._fallback(module, payload, reason="mcp_error", error=str(exc))

    async def _fallback(
        self,
        module: RepoNode,
        payload: dict[str, Any],
        reason: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        result = await super().run(module, payload)
        result["source"] = "subprocess"
        result["fallback_reason"] = reason
        if error:
            result["fallback_error"] = error
        return result
```

- [ ] **Step 4: Export from security package**

Modify `sahiixx_agency/adapters/security/__init__.py`:

```python
"""Security adapters."""

from sahiixx_agency.adapters.security.runner import SecurityAdapter, run_security_module
from sahiixx_agency.adapters.security.t3mp3st import T3mp3stAdapter
from sahiixx_agency.adapters.security.t3mp3st_mcp import T3mp3stMcpAdapter

__all__ = ["SecurityAdapter", "T3mp3stAdapter", "T3mp3stMcpAdapter", "run_security_module"]
```

- [ ] **Step 5: Run the tests to verify they pass**

Run:

```bash
pytest tests/adapters/test_t3mp3st_mcp.py -v
```

Expected: all `PASS`.

- [ ] **Step 6: Commit**

```bash
git add sahiixx_agency/adapters/security/t3mp3st_mcp.py sahiixx_agency/adapters/security/__init__.py tests/adapters/test_t3mp3st_mcp.py
git commit -m "feat(security): add T3MP3ST MCP adapter with subprocess fallback"
```

---

### Task 5: Update `config/agency.yaml`

**Files:**
- Modify: `config/agency.yaml`

**Interfaces:**
- Consumes: existing ecosystem and routing rule schemas.
- Produces: `t3mp3st` and `hiring_agent` ecosystem entries + routing rules.

- [ ] **Step 1: Add ecosystem entries**

Insert after the `moltworker` ecosystem entry in `config/agency.yaml`:

```yaml
  # ── Security Adapters ──
  t3mp3st:
    repo: T3MP3ST
    owner: elder-plinius
    url: https://github.com/elder-plinius/T3MP3ST
    role: "Autonomous red-team meta-harness — recon → exploit → report"
    bus_channel: "security.*"
    protocol: mcp+subprocess
    priority: 2
    tags: [security, redteam, pentest, mcp, t3mp3st]
    adapter_config:
      default_mode: lite
      blocked_targets:
        - localhost
        - 127.0.0.1
        - ::1
        - 0.0.0.0
        - 10.0.0.0/8
        - 172.16.0.0/12
        - 192.168.0.0/16
        - fc00::/7
      allow_local: false

  # ── HR / Hiring Agents ──
  hiring_agent:
    repo: hiring-agent
    owner: interviewstreet
    url: https://github.com/interviewstreet/hiring-agent
    role: "AI hiring agent — resume + GitHub profile evaluation and scoring"
    bus_channel: "hr.*"
    protocol: python-lib
    priority: 2
    tags: [hiring, hr, resume, evaluation, hackerrank]
```

- [ ] **Step 2: Add routing rules**

Append to `routing_rules` in `config/agency.yaml`:

```yaml
  - pattern: "t3mp3st|red.team|offensive|0-day|zero.day|exploit|pentest|recon|security"
    target: t3mp3st
  - pattern: "resume|candidate|hire|hiring|evaluate.profile|screen|recruit"
    target: hiring_agent
```

- [ ] **Step 3: Validate YAML syntax**

Run:

```bash
python -c "import yaml; yaml.safe_load(open('config/agency.yaml'))" && echo "YAML OK"
```

Expected: prints `YAML OK`.

- [ ] **Step 4: Commit**

```bash
git add config/agency.yaml
git commit -m "feat(config): register T3MP3ST and hiring-agent in agency.yaml"
```

---

### Task 6: Add routing and adapter-selection tests

**Files:**
- Modify: `tests/test_core.py`

**Interfaces:**
- Consumes: `TaskRouter`, `AgencyConfig`, fake modules.
- Produces: tests proving red-team and hiring intents route to the correct modules.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_core.py`:

```python
import pytest

from sahiixx_agency.core.bus import MessageBus
from sahiixx_agency.core.models import AgencyConfig, RepoCategory, RepoNode
from sahiixx_agency.core.registry import RepoRegistry
from sahiixx_agency.core.router import TaskRouter


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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/test_core.py::test_router_resolves_red_team_intent_to_t3mp3st tests/test_core.py::test_router_resolves_hiring_intent_to_hiring_agent -v
```

Expected: `PASS` if the config resolves correctly; `FAIL` only if routing logic is broken.

- [ ] **Step 3: Run the tests to verify they pass**

Run the same command again.

Expected: `PASS`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_core.py
git commit -m "test(routing): cover T3MP3ST and hiring-agent routing rules"
```

---

### Task 7: Run full test suite and fix regressions

**Files:**
- All of the above.

- [ ] **Step 1: Run the full test suite**

Run:

```bash
pytest tests/ -v
```

Expected: all tests pass. If any fail, fix the underlying issue before proceeding.

- [ ] **Step 2: Run lint checks**

Run:

```bash
ruff check sahiixx_agency tests
```

Expected: no errors. If any, fix them.

- [ ] **Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: address test/lint regressions for T3MP3ST integration"
```

---

## Self-Review

**1. Spec coverage:**
- Target scoping and validation — Task 2.
- Lite/full arsenal gating — Task 3.
- Approval token with constant-time comparison — Task 1 and Task 3.
- MCP-native path with fallback — Task 4.
- `agency.yaml` registration of both modules — Task 5.
- Routing rules — Task 5 and Task 6.
- Tests — Tasks 1, 2, 3, 4, 6, 7.

**2. Placeholder scan:**
- No "TBD", "TODO", or "implement later".
- All code blocks contain concrete implementations.
- All commands include expected output.

**3. Type consistency:**
- `validate_target` signature is consistent across tasks.
- `_validate_payload` returns `(dict[str, str] | None, dict[str, Any] | None)` and is used by both subprocess and MCP adapters.
- `T3mp3stMcpAdapter` inherits from `T3mp3stAdapter` so `_validate_payload` and `_fallback` share the same base behavior.

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-05-t3mp3st-hiring-agent-integration.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

Auto-mode is active, so I will proceed with **Subagent-Driven** execution.

