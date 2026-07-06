# Design: T3MP3ST + Hiring-Agent Integration into OPA

**Date:** 2026-07-05  
**Status:** Draft pending implementation planning  
**Author:** Kimi Code CLI via Superpowers brainstorming workflow

## 1. Scope & Goals

This design registers two external repositories as first-class modules in the One Person Agency (OPA) ecosystem:

- **[`elder-plinius/T3MP3ST`](https://github.com/elder-plinius/T3MP3ST)** — autonomous red-team / offensive-security meta-harness (TypeScript + Node.js + MCP).
- **[`interviewstreet/hiring-agent`](https://github.com/interviewstreet/hiring-agent)** — HackerRank open-source AI hiring agent for resume and GitHub profile evaluation (Python).

Goals:

1. Register both repos in OPA with correct routing rules.
2. Harden T3MP3ST execution behind OPA-level safety gates (target scoping, lite/full arsenal control, human-approval token).
3. Add an MCP-native invocation path for T3MP3ST so it can be reached as an MCP tool server, falling back to subprocess execution when unavailable.
4. Keep the change set scoped to `sahiixx-agency` config, adapters, and tests.
5. Do not modify external repositories.

## 2. T3MP3ST Safety-Hardened Subprocess Adapter

### 2.1 New file

`sahiixx_agency/adapters/security/t3mp3st.py`

### 2.2 Behavior

The adapter extends the existing `SecurityAdapter` and performs strict payload validation before any subprocess is spawned:

| Field | Required | Default | Validation |
|-------|----------|---------|------------|
| `target` | yes | — | Non-empty string; syntactically validated as a host, IP, or URL and checked against the `blocked_targets` block-list. Blocked values include `localhost`, `127.0.0.1`, `::1`, `0.0.0.0`, and any RFC 1918 / RFC 4193 CIDR range unless `adapter_config.allow_local=true`. Validation uses Python’s `ipaddress` module for CIDR matching; no outbound network probe is performed. |
| `mode` | no | `"lite"` | `"lite"` or `"full"`. |
| `approval` | conditional | `null` | Required when `mode="full"`. Must match the `T3MP3ST_APPROVAL_TOKEN` configured in `AgencyConfig` / environment. Comparison uses a constant-time string comparison (e.g., `hmac.compare_digest`) to resist timing attacks. |
| `command` | no | `"run"` | Maps to npm script (`start`, `dev`, `cli`) or direct CLI invocation. |
| `timeout` | no | `180` | Same override semantics as `SecurityAdapter`. |

Environment variables injected into the T3MP3ST subprocess:

```bash
T3MP3ST_TARGET=<target>
T3MP3ST_FULL_ARSENAL=0|1        # 1 only when mode=full and approval valid
T3MP3ST_EGRESS_POLICY=scoped
```

### 2.3 Error responses

Validation failures return immediately without spawning a subprocess:

- `missing_target` — no `target` provided.
- `invalid_target` — target is not a valid host/URL or is in the local block-list.
- `approval_required` — `mode=full` without valid approval token.
- `approval_mismatch` — provided approval token does not match config.

### 2.4 Execution path

1. Validate payload.
2. Clone/pull T3MP3ST via existing `CloneManager`.
3. Inspect `package.json` with existing `RepoInspector`.
4. Run `npm install` if `node_modules` is absent.
5. Run the selected npm script or CLI command with the injected environment.
6. Return structured result including the safety mode applied.

## 3. T3MP3ST MCP-Native Adapter

### 3.1 New file

`sahiixx_agency/adapters/security/t3mp3st_mcp.py`

### 3.2 Behavior

Implements an MCP client wrapper around T3MP3ST’s own MCP server. Uses the `mcp` package already declared in OPA dependencies.

Exposed OPA tool schema:

```json
{
  "name": "security_recon",
  "description": "Run T3MP3ST reconnaissance against a scoped target",
  "inputSchema": {
    "type": "object",
    "properties": {
      "target": { "type": "string" },
      "mode": { "type": "string", "enum": ["lite", "full"] },
      "approval": { "type": "string" }
    },
    "required": ["target"]
  }
}
```

### 3.3 Fallback

If the MCP server cannot be started or the tool call fails, the adapter falls back to the subprocess adapter in section 2. This ensures OPA still works even if T3MP3ST’s MCP surface changes or is unavailable.

### 3.4 Safety gates

The MCP path applies the same validation rules as the subprocess path before forwarding the call. The approval token is checked in OPA, not delegated to T3MP3ST.

## 4. Hiring-Agent Registration

`interviewstreet/hiring-agent` is a Python 3.11+ project. Initial integration uses the existing generic `BaseAdapter` because the repo likely exposes a `main.py` or comparable entrypoint.

No custom adapter is required unless the repository’s execution semantics are non-standard (e.g., requires a specific resume file path argument or a custom config file). If non-standard semantics are discovered during implementation, a thin `HiringAgentAdapter` will be added.

## 5. Configuration Changes

### 5.1 New ecosystem entries in `config/agency.yaml`

```yaml
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

### 5.2 New routing rules

Append to `routing_rules`:

```yaml
  - pattern: "t3mp3st|red.team|offensive|0-day|zero.day|exploit|pentest|recon|security"
    target: t3mp3st
  - pattern: "resume|candidate|hire|hiring|evaluate.profile|screen|recruit"
    target: hiring_agent
```

### 5.3 New environment variable

| Variable | Description | Default |
|----------|-------------|---------|
| `T3MP3ST_APPROVAL_TOKEN` | Token required to authorize `mode=full` arsenal. | `null` |

Add to `AgencyConfig` in `sahiixx_agency/core/models.py`:

```python
t3mp3st_approval_token: str | None = Field(default=None)
```

## 6. Testing Strategy

| Test | File | What it verifies |
|------|------|------------------|
| Payload validation | `tests/adapters/test_t3mp3st.py` | Missing target, invalid target, local block-list, full-arsenal approval required, valid full-arsenal passes. |
| Subprocess execution | `tests/adapters/test_t3mp3st.py` | Adapter injects correct env vars and returns structured result. Uses monkeypatched `subprocess.run`. |
| MCP fallback | `tests/adapters/test_t3mp3st_mcp.py` | If MCP server fails, adapter falls back to subprocess adapter. |
| Routing rules | `tests/test_core.py` | Intents containing red-team keywords resolve to `t3mp3st`; hiring intents resolve to `hiring_agent`. |
| Config load | `tests/test_core.py` | New `t3mp3st_approval_token` is parsed from env/config correctly. |

No tests will perform live network calls or run real T3MP3ST tools.

## 7. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Subprocess execution of offensive tools can harm networks. | Enforce target scoping, block local networks by default, require approval token for full arsenal, default to lite mode. |
| T3MP3ST is brand-new and AGPL-3.0. | Verify license compatibility before bundling or redistribution; OPA only clones and runs it on demand, which is generally permitted under AGPL for self-hosted use, but legal review is advised. |
| MCP tool names may differ from assumed `security_recon`. | Implement runtime tool discovery and fallback to subprocess if the expected tool is missing. |
| `hiring-agent` may require non-standard invocation. | Inspect after clone; add a thin adapter only if needed. |

## 8. Implementation Order

1. Update `AgencyConfig` with `t3mp3st_approval_token`.
2. Create `T3mp3stAdapter` and tests.
3. Create `T3mp3stMcpAdapter` and tests.
4. Update `config/agency.yaml` with ecosystem entries and routing rules.
5. Add hiring-agent ecosystem entry and routing rule.
6. Run full test suite and fix regressions.
7. Invoke `writing-plans` for the next implementation session.

## 9. Open Questions for Implementation

- What is the exact T3MP3ST npm script name for CLI headless runs? (`start`, `dev`, `cli`, or another?)
- What is the exact MCP tool name T3MP3ST exposes for reconnaissance?
- Does `hiring-agent` require a specific resume file path argument, or does it read from stdin/config?

These will be answered by cloning the repositories during implementation.
