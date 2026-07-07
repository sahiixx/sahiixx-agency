# What I Do

## My products and offers
1. sahiixx-agency CLI — `opa` commands for sync, dispatch, registry, workflows, LLM, Telegram.
2. OPA FastAPI server — REST API with `/health`, `/stats`, `/dispatch`, `/registry`, workflows, SSE notifications.
3. OPA MCP server — exposes agency tools to Claude, Cursor, Copilot via Model Context Protocol.
4. OPA React dashboard — D3 repo universe, workflows, metrics, approvals, LLM playground, todos.
5. OPA Telegram bots — general agency bot and Career-Ops dispatcher.

## Current quarter goals (update every 90 days)
- Registry goal: 250+ auto-discovered modules with working adapters for the top 10 categories.
- Integration goal: 3 fully operational MCP adapters, 5 external repo clones running end-to-end.
- Build goal: Get the full stack (API + MCP + dashboard) deployable on Docker and Render.

## What I'm saying YES to this quarter
- Adapter-first integrations (T3MP3ST, Career-Ops, Hiring-Agent, OpenMontage, HTML-Anything).
- Deterministic smoke tests and pytest coverage before any new route lands.
- Shipping docs, pitch decks, and OS templates that make the project usable by others.

## What I'm saying NO to this quarter
- Polishing the dashboard UI before the backend is rock solid.
- Adding auth/billing/enterprise features before the core framework is stable.
- Building new agent features that don't have a concrete module to route to.

## The one thing that matters most
If only one thing gets done this quarter, it is: make the OPA API and dashboard serve a truthful, up-to-date registry and route every supported intent to a working adapter with passing tests.
