# Windows stack notes (Sahil workstation)

## Entrypoint / dispatch (2026-07-16)

- `sahiixx_agency.discovery.entrypoint` runs Python modules with **`sys.executable`** (OPA venv), not bare `python`/`pip` on PATH.
- Auto `pip install` on infer is **disabled** so monorepo roots (e.g. `agency-agents` with a jarvis `pyproject.toml`) do not install the wrong package on every dispatch.
- `RepoInspector` in `core/runner.py` uses the same interpreter.
- Local clone for smoke: `data/repos/sahiixx/agency-agents/main.py` (offline agent inventory). Full missions still use `python agency.py --mission ...` after installing deepagents.

## Bring-up

```powershell
C:\Users\sahii\scripts\start-stack.ps1 -StartOpa -StartModularOs
C:\Users\sahii\scripts\verify-stack.ps1 -SkipRealFire
```

WSL services are most reliable via the **WSL eth IP** (`wsl hostname -I`) — Windows `127.0.0.1` port proxy sometimes handles GET but drops POST. `verify-stack.ps1` prefers the WSL IP automatically.

`.wslconfig` has `autoMemoryReclaim=disabled` (applied 2026-07-16). Needs one `wsl --shutdown` + restart to take effect.

## WSL services

| Unit | Port |
|------|------|
| estate-api | 3001 |
| estate-whatsapp | 3002 (`0.0.0.0`) |
| sahiix-voice | 3003 (`0.0.0.0`) |
| sahiix-os | 3005 |
| openclaw-gateway | 18789 (WSL localhost) |

WhatsApp/voice were patched to bind `0.0.0.0` so Windows can reach them via WSL port forward.

## NEXUS HARD fire (2026-07-16)

`POST http://127.0.0.1:3005/api/nexus/fire`

| Body | Behavior |
|------|----------|
| `{}` or `{ "dry_run": true }` | Plan queue from estate leads (fallback HNW stub). **No send.** |
| `{ "dry_run": false, "confirm": "FIRE", "limit": 1 }` | Real send via WhatsApp bot `POST /outbound` → OpenClaw bridge. Max `limit` 20. |

Logs: `~/projects/sahiix-estate/fire-logs/` on WSL.

## deepagents (agency-agents)

Installed into OPA venv:

```text
pip install -e data/repos/sahiixx/agency-agents/deepagents/libs/deepagents
pip install langchain-ollama
```

OPA smoke entrypoint: `main.py` (inventory + `deepagents: ok`). Full `agency.py --list-agents` may still need `sahiixx-bus` and a running Ollama.
