# Weekly Brief: 2026-07-07

## What's happening this week
The full OPA stack is now running locally after resolving the 8080 zombie process and registry drift. The html-anything adapter and route are complete. This week is about locking in the dashboard experience, regenerating any stale docs, and choosing the next high-impact module to integrate.

## What needs to ship
- Verify dashboard loads the 201-module graph and all API endpoints respond correctly.
- Re-run combined pytest + smoke test after any final config changes.
- Decide next adapter target (Letta-Code, RelayMux, or Claude-Obsidian).
- Publish or commit the filled-in One-Person Company OS templates for OPA.

## What I'm NOT doing this week
- Adding auth or multi-tenancy to the API.
- Re-architecting the registry storage format.
- Building a new external website or landing page.

## Current state
- Registry: 201 modules, 10 categories.
- Tests: 98 passed, smoke test 3/3.
- API: running on http://localhost:8082.
- Dashboard: running on http://localhost:3000.

## The one thing
If I only get one thing done this week, it must be: confirm the dashboard is fully usable against the 201-module API and pick the next adapter to ship.
