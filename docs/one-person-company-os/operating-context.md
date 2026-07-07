# Operating Context

## This week (updated every Monday)
- Focus: Stabilize the full-stack run (API + dashboard) and finish the html-anything integration.
- Open loops: Port 8080 zombie process issue resolved; dashboard now targets 8082; need to verify dashboard consumes graph data.
- Decisions made: Use port 8082 as the canonical local API port until the 8080 issue is fully understood. Deterministic simulation fallback is acceptable for adapters when the underlying repo is not installed.

## Active projects
- OPA full-stack stabilization — status: API and dashboard running, needs dashboard data verification; deadline: this week.
- HTML-Anything adapter — status: adapter created, route added, tests passing; deadline: done.
- One-Person Company OS templates — status: extracted from guide, filled in for OPA; deadline: today.
- Registry expansion — status: 201 modules; goal 250; deadline: end of quarter.

## Recent decisions log
- 2026-07-07: Switched local API port from 8080 to 8082 to avoid a stubborn zombie process and inconsistent module counts.
- 2026-07-07: Confirmed registry has 201 modules; regenerated report and pitch deck.
- 2026-07-07: Filled in the One-Person Company OS templates for sahiixx-agency.

## Things I keep changing my mind on (red flag list)
- Whether to keep the dashboard `dist/` directory tracked in Git. Decision: keep it for now, revisit before public release.
- Whether to expose the full T3MP3ST arsenal via MCP. Decision: keep full arsenal internal; only expose `security_recon`.

## Wins worth remembering
- - 201 modules registered in the agency registry
- T3MP3ST, Career-Ops, Hiring-Agent, OpenMontage, HTML-Anything adapters shipped
- pytest suite: 98 passed, smoke test 3/3 passed
- API + dashboard running on localhost:8082 + localhost:3000
