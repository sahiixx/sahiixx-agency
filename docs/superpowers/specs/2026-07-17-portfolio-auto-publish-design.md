# Portfolio Auto-Publish — Design Spec

**Date:** 2026-07-17 · **Repo:** sahiixx-agency (OPA) · **Status:** implemented 2026-07-18 (merged `0f4512f`; E2E-verified live publish of `relaymux`)

## 1. Goal

When a new module ships (appears in OPA's registry after a sync), OPA drafts a curated
case-study entry for the portfolio site, inserts it into the portfolio's data file,
validates the build, deploys to Cloudflare Pages, and notifies the outcome — no human in
the loop, with a config kill-switch and dry-run mode.

Live site: `https://sahiix-portfolio.pages.dev` · Source: `C:\Users\sahii\Projects\portfolio`
(Vite + TS, data in `src/data.ts`, deploy via `npm run deploy` → `wrangler pages deploy dist`).

## 2. Decisions locked

- **"Shipped" = newly discovered in the registry** on any `sync_repos()` run whose
  pre-sync registry was non-empty. First-ever sync (empty → full) establishes the
  baseline silently; it must not fan out dozens of publish events.
- **Publish path = local edit + wrangler deploy.** The portfolio is not GitHub-connected;
  Pages deploys happen by direct upload from this machine, and wrangler is already
  authenticated here. No GitHub-write or Cloudflare-API client is built (none exists in
  OPA today — YAGNI).
- **Entries are LLM-drafted**, because `Project` is a rich case-study interface
  (problem / architecture / highlights / statusNote). Raw registry metadata would read
  as junk next to the four hand-written entries. The LLM drafts from registry metadata
  plus the module's README (local clone under `data/repos/` when present, else raw
  GitHub GET — read-only, matches existing usage).
- **Architecture = event workflow + specialized adapter** (approach A below).

## 3. Approaches considered

| | A. Event workflow + adapter (chosen) | B. Direct hook in `sync_repos` | C. Deploy hook + GitHub Actions |
|---|---|---|---|
| Shape | `sync_repos` diffs → `bus.publish("registry.module_added")` → event workflow → dispatch `portfolio_publisher` adapter | `sync_repos` calls adapter inline, no workflow | Pages becomes GitHub-connected; GH Action generates content on push |
| Pros | Uses the workflow system (visible in dashboard/API, JSON-defined, same pattern as site-monitor); bus plumbing already whitelists `registry.*` topics; decoupled | Fewest moving parts | Zero new OPA code |
| Cons | Dispatch is queue-and-forget (adapter must report its own outcome) | Invisible to workflow UI, bypasses the system we just invested in | Re-platforms the portfolio, content generation moves into CI YAML, two-platform coupling |

B is a fallback if the event path proves broken. C is rejected as infra churn for no gain.

## 4. Architecture

```
opa sync / API / telegram / jarvis
        │
        ▼
AgencyEngine.sync_repos()                     [core/engine.py]
   before = set(registry ids)  (skip events if empty)
   discover()
   new = after − before
   for each new module:
      bus.publish("registry.module_added", module payload)
        │
        ▼  (engine._on_bus_message already routes registry.* → workflows.trigger_event)
portfolio-publisher workflow                   [data/workflows/portfolio-publisher.json]
   trigger: event / event_topic: registry.module_added
   one dispatch step: intent "publish portfolio entry for <name>"
        │
        ▼  (routing rule → portfolio_publisher; task queued → worker executes)
portfolio_publisher adapter                    [adapters/portfolio_publisher_adapter.py]
   gates → draft entry (LLM) → insert into data.ts → build → deploy → commit/push → notify
```

## 5. Components

### 5.1 Sync diff + event (`core/engine.py::sync_repos`)
- Snapshot `set(self.registry._modules.keys())` before `discover()`, diff after.
- If the before-set is empty, publish nothing (baseline sync).
- Else for each new module: `bus.publish(BusMessage(topic="registry.module_added",
  payload=node.model_dump(mode="json")))` and keep the existing `registry.sync`
  memory-event log. Renames/removals are ignored (additions only).

### 5.2 Workflow definition (`data/workflows/portfolio-publisher.json`)
- `trigger: "event"`, `event_topic: "registry.module_added"`, `enabled: true`.
- Single `dispatch` step whose `intent_template` renders
  `publish portfolio entry for {name}` (context = event payload; single-brace
  substitution per `workflows.py:354`). A new routing
  rule in `agency.yaml` pins that intent to `portfolio_publisher`.
- No workflow-level `notify` step: dispatch completes on enqueue, so the step cannot
  report the real outcome. The adapter owns outcome notification (5.3).

### 5.3 `portfolio_publisher` adapter (`adapters/portfolio_publisher_adapter.py`)
Standalone specialized adapter, registered in `_SPECIALIZED_ADAPTERS` (engine.py) per
repo AGENTS.md. Config block `portfolio_publisher` in `agency.yaml`:
`enabled` (default false until first verified run), `dry_run` (default true initially),
`repo_path` (`C:\Users\sahii\Projects\portfolio`), `ignore` (list of module ids).

Pipeline, in order, each step aborting with notify-on-failure:
1. **Gates** — skip (and log why) when: `enabled` false; module in `ignore`; fork or
   missing description (`RepoNode` carries `is_fork`; there is no `archived` flag);
   slug already present in `src/data.ts` (dedup).
2. **Pre-flight** — `git -C repo status --porcelain src/data.ts` must be clean; a dirty
   data file means the user is mid-edit → abort + notify, never stomp.
3. **Context** — module registry payload + README text (local `data/repos/<name>`
   clone if present, else raw GitHub GET; both read-only).
4. **Draft** — OPA LLM (existing `core/llm.py` provider chain) prompted to return strict
   JSON for a pydantic `ProjectEntry` mirroring `Project` minus `image`: id (kebab slug),
   index (next after max existing, zero-padded), name, tagline, description,
   longDescription (2–3 paragraphs), problem, architecture, statusNote, highlights (3–5),
   role, status, stack, year (current), url (homepage else repo URL), accent (from a
   fixed palette, rotating by existing entry count). Validation failure → abort + notify.
5. **Insert** — render the entry as a TS object literal in the file's existing style and
   insert before the marker line `// __OPA_PORTFOLIO_INSERT__` inside the `projects`
   array (one-time marker added to `src/data.ts` by this change; see 5.4). Keep the
   original file content in memory for rollback.
6. **Build** — `npm run build` in the portfolio repo (timeout, captured output). On
   failure: restore original `data.ts`, notify failure with the build error tail.
7. **Commit** — `git add src/data.ts && git commit -m "feat: add <name> to selected
   work [opa]"` in the portfolio repo. Committing before deploy keeps the working tree
   clean (a dirty tree would trip the pre-flight gate on the next publish).
8. **Deploy** — `npx wrangler pages deploy dist` (skip the second build in
   `npm run deploy`). On failure: the entry stays committed locally, notify failure
   (site untouched; retry with `npm run deploy` in the portfolio repo).
9. **Push** — `git push`, warning-only on failure (live site is already deployed).
10. **Notify** — success/failure via the configured notification channels
   (`telegram` when a token is configured, else `sse` + `console`), including module
   name and the step reached. Under `dry_run`, the pipeline stops before step 5: the
   rendered entry is sent to the notification channels and nothing on disk changes.

Approval gate: the publisher task must not be parked by the high/critical-risk approval
gate (`config.approval`) — implementation must verify the module's risk classification
and keep it below the threshold, since a parked task silently defeats the feature.

### 5.4 Portfolio repo one-time edit
Insert the single marker comment `// __OPA_PORTFOLIO_INSERT__` immediately before the
closing bracket of the `projects` array in `src/data.ts`. No layout code touched
(matches that repo's CLAUDE.md rule: "edit the site here"). Committed manually as part
of implementation.

### 5.5 Config / routing / registration (`config/agency.yaml`, `core/engine.py`)
- Ecosystem entry `portfolio_publisher` (role, capabilities, category, bus_channel
  `publish.*`), same shape as `web_intel`.
- Routing rule: pattern `publish portfolio|portfolio entry|add.*(to|2) selected work`
  → `portfolio_publisher`, placed before generic fallbacks.
- Factory registered in `_SPECIALIZED_ADAPTERS`.

## 6. Curation & dedup rules

- Skip: forks, archived repos, empty descriptions, `ignore` list, already-present slugs.
- Everything else publishes. The portfolio stays curated because the LLM writes real
  case-study copy and the gates keep junk repos out; `dry_run` lets us eyeball entries
  before the first live run.
- Repeat syncs are idempotent: the slug check in `data.ts` is the source of truth.

## 7. Error handling

| Failure | Behaviour |
|---|---|
| LLM/validation error | Abort, no file touched, notify |
| `data.ts` dirty | Abort, notify (protects user's uncommitted edits) |
| Marker missing | Abort, notify (never guess an insertion point) |
| Build fails | Restore original file, notify with error tail |
| Deploy fails | Keep local commit, notify; site not updated |
| Push fails | Warn in notification; deploy already succeeded |
| Adapter exception | Task fails; notify failure with exception summary |

## 8. Testing

- `sync_repos` diff: mock `registry.discover`; assert one `registry.module_added` publish
  per new id, none on baseline (empty before-set), none on re-sync with no changes.
- Adapter, with temp portfolio copy and mocked subprocess/LLM: entry renders with all
  required `Project` fields; dedup skip; ignore-list skip; dirty-file abort; marker
  insertion point; build-failure rollback restores bytes; dry_run writes nothing.
- Workflow JSON loads and carries `trigger: "event"` + topic (same style as existing
  workflow tests).
- Full suite (`pytest tests/ -q`, currently 483) stays green; new tests added alongside.
- Final implementation step: run the adapter in `dry_run` against the real portfolio
  repo with a real module, eyeball the rendered entry, then set `dry_run: false` and
  `enabled: true`.

## 9. Non-goals (YAGNI)

- No GitHub PR/contents-API flow, no Cloudflare API client.
- No updates to the `systems[]` panel, no screenshot/`image` generation, no edits to
  existing hand-written entries.
- No custom-domain (`sahiix.os`) work.
- No removal/rename propagation (additions only).

## 10. Risks

- **LLM entry quality varies** → mitigated by `dry_run` first runs and strict schema.
- **Wrangler auth expires** → deploy step fails loudly with notify; entry stays committed.
- **First-sync event flood** → baseline guard (empty before-set publishes nothing).
- **Live-site blast radius** → kill-switch `enabled`, `dry_run`, build-gate rollback,
  dirty-file abort, and notify on every outcome.
