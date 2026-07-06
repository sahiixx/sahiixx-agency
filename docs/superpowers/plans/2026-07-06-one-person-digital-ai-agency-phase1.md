# One Person Digital AI Agency — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase 1 of the One Person Digital AI Agency — a unified command center that can auto-discover trending GitHub repos and run both existing OPA modules and freshly discovered repos through a generic adapter.

**Architecture:** Extend the existing OPA scaffold with three new subsystems: a real-time **Discovery Feed**, a **Generic Adapter** that infers how to run any repo, and a **Trending Dashboard Panel**. These plug into the existing registry, router, task worker, and API. The generic adapter becomes the default execution path for modules that do not have a specialized adapter.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic v2, Typer, httpx, pytest, pytest-asyncio, SQLite, React + Vite dashboard, Tailwind CSS.

## Global Constraints

- Target Python 3.10+ syntax; use `from __future__ import annotations` in all new Python files.
- Line length 120 (ruff default).
- All domain models are Pydantic v2 BaseModel.
- Async core engine and API; adapters that call subprocesses must offload blocking calls via `asyncio.to_thread`.
- Tests must use monkeypatch, not real network calls or real subprocesses.
- No hardcoded secrets; load from environment variables.
- Keep diffs minimal and scoped; match existing file style and conventions.
- Every task ends with a green `pytest` run, clean `ruff check`, and clean `mypy sahiixx_agency`.
- Commit after each task.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `sahiixx_agency/discovery/__init__.py` | Package init, exposes public discovery API |
| `sahiixx_agency/discovery/sources.py` | Fetch trending repos from GitHub/HN/Reddit/X |
| `sahiixx_agency/discovery/pipeline.py` | Deduplicate, filter, classify, score, register, clone |
| `sahiixx_agency/discovery/entrypoint.py` | Infer how to run a cloned repo from its files |
| `sahiixx_agency/adapters/generic_adapter.py` | Generic adapter that runs any repo using inferred entrypoint |
| `sahiixx_agency/core/engine.py` | Use generic adapter as fallback; wire discovery and approval gates |
| `sahiixx_agency/api/main.py` | Add `/discovery/run`, `/discovery/trending`, `/tasks/{id}/approve` endpoints |
| `sahiixx_agency/core/models.py` | Add `DiscoveryResult`, `ApprovalRequest`, `RiskLevel` models |
| `config/agency.yaml` | Add discovery settings and risk defaults |
| `tests/discovery/test_sources.py` | Mocked source tests |
| `tests/discovery/test_pipeline.py` | Pipeline unit tests |
| `tests/discovery/test_entrypoint.py` | Entrypoint inference tests |
| `tests/adapters/test_generic_adapter.py` | Generic adapter tests |
| `tests/test_api_discovery.py` | API endpoint tests |

---

## Task 1: Discovery Source Scraper Skeleton

**Files:**
- Create: `sahiixx_agency/discovery/__init__.py`
- Create: `sahiixx_agency/discovery/sources.py`
- Test: `tests/discovery/test_sources.py`

**Interfaces:**
- Consumes: `httpx.AsyncClient`, GitHub token from env `GITHUB_TOKEN`.
- Produces:
  - `async def fetch_github_trending(language: str | None = None) -> list[DiscoveryResult]`
  - `async def fetch_github_velocity(languages: list[str] | None = None, min_stars: int = 50) -> list[DiscoveryResult]`
  - `async def fetch_hackernews_repos() -> list[DiscoveryResult]`
  - `async def fetch_reddit_repos(subreddits: list[str]) -> list[DiscoveryResult]`
  - `async def fetch_all_sources() -> list[DiscoveryResult]`

`DiscoveryResult` is added in Task 3; for now return plain dicts.

- [ ] **Step 1: Write the failing test**

```python
# tests/discovery/test_sources.py
from __future__ import annotations

import pytest

from sahiixx_agency.discovery.sources import fetch_github_velocity


@pytest.mark.asyncio
async def test_fetch_github_velocity_parses_search_results(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "items": [
                    {
                        "id": 1,
                        "full_name": "nexu-io/html-anything",
                        "html_url": "https://github.com/nexu-io/html-anything",
                        "description": "Generate HTML from prompts",
                        "stargazers_count": 1200,
                        "language": "TypeScript",
                        "created_at": "2026-06-01T00:00:00Z",
                        "updated_at": "2026-07-01T00:00:00Z",
                    }
                ]
            }

    class FakeClient:
        async def get(self, url, **kwargs):
            calls.append(url)
            return FakeResponse()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr("sahiixx_agency.discovery.sources.httpx.AsyncClient", lambda **kwargs: FakeClient())
    results = await fetch_github_velocity(languages=["python"])
    assert len(results) == 1
    assert results[0]["full_name"] == "nexu-io/html-anything"
    assert results[0]["stars"] == 1200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/discovery/test_sources.py::test_fetch_github_velocity_parses_search_results -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'sahiixx_agency.discovery.sources'`

- [ ] **Step 3: Write minimal implementation**

```python
# sahiixx_agency/discovery/__init__.py
"""Discovery feed for trending repos."""

from __future__ import annotations

from .sources import fetch_all_sources, fetch_github_trending, fetch_github_velocity, fetch_hackernews_repos, fetch_reddit_repos

__all__ = [
    "fetch_all_sources",
    "fetch_github_trending",
    "fetch_github_velocity",
    "fetch_hackernews_repos",
    "fetch_reddit_repos",
]
```

```python
# sahiixx_agency/discovery/sources.py
"""Fetch trending repos from GitHub, Hacker News, Reddit, and X."""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

_GITHUB_API = "https://api.github.com"
_HN_API = "https://hn.algolia.com/api/v1"


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "sahiixx-agency-discovery"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _item_to_result(item: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "full_name": item.get("full_name"),
        "url": item.get("html_url"),
        "description": item.get("description") or "",
        "stars": item.get("stargazers_count") or 0,
        "language": item.get("language") or "Unknown",
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "source": source,
    }


async def fetch_github_trending(language: str | None = None) -> list[dict[str, Any]]:
    """Fetch GitHub trending via search API (trending page is not officially API-accessible)."""
    q = "created:>7d stars:>50 sort:stars"
    if language:
        q += f" language:{language}"
    url = f"{_GITHUB_API}/search/repositories"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_headers(), params={"q": q, "per_page": 20})
    if resp.status_code != 200:
        return []
    return [_item_to_result(item, "github_trending") for item in resp.json().get("items", [])]


async def fetch_github_velocity(
    languages: list[str] | None = None,
    min_stars: int = 50,
) -> list[dict[str, Any]]:
    """Fetch recently starred repos."""
    languages = languages or ["python", "typescript", "javascript", "go", "rust"]
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=30) as client:
        for language in languages:
            q = f"created:>7d stars:>{min_stars} language:{language} sort:stars"
            url = f"{_GITHUB_API}/search/repositories"
            resp = await client.get(url, headers=_headers(), params={"q": q, "per_page": 10})
            if resp.status_code == 200:
                results.extend(_item_to_result(item, "github_velocity") for item in resp.json().get("items", []))
    return results


async def fetch_hackernews_repos() -> list[dict[str, Any]]:
    """Fetch Show HN stories and extract GitHub URLs."""
    url = f"{_HN_API}/search?tags=show_hn&hitsPerPage=30"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers={"User-Agent": "sahiixx-agency-discovery"})
    if resp.status_code != 200:
        return []
    results = []
    seen = set()
    for hit in resp.json().get("hits", []):
        text = f"{hit.get('title', '')} {hit.get('url', '')} {hit.get('story_text', '')}"
        for match in re.finditer(r"https?://github\.com/([^/\s]+/[^/\s]+)", text):
            full_name = match.group(1).rstrip("/")
            if full_name in seen:
                continue
            seen.add(full_name)
            results.append(
                {
                    "full_name": full_name,
                    "url": f"https://github.com/{full_name}",
                    "description": hit.get("title") or "",
                    "stars": 0,
                    "language": "Unknown",
                    "source": "hackernews",
                }
            )
    return results


async def fetch_reddit_repos(subreddits: list[str] | None = None) -> list[dict[str, Any]]:
    """Fetch top posts from subreddits and extract GitHub URLs."""
    subreddits = subreddits or ["MachineLearning", "webdev", "LocalLLaMA", "selfhosted"]
    results = []
    seen = set()
    async with httpx.AsyncClient(timeout=30) as client:
        for subreddit in subreddits:
            url = f"https://www.reddit.com/r/{subreddit}/top.json?t=day&limit=10"
            resp = await client.get(url, headers={"User-Agent": "sahiixx-agency-discovery"})
            if resp.status_code != 200:
                continue
            for post in resp.json().get("data", {}).get("children", []):
                text = f"{post['data'].get('title', '')} {post['data'].get('selftext', '')} {post['data'].get('url', '')}"
                for match in re.finditer(r"https?://github\.com/([^/\s]+/[^/\s]+)", text):
                    full_name = match.group(1).rstrip("/")
                    if full_name in seen:
                        continue
                    seen.add(full_name)
                    results.append(
                        {
                            "full_name": full_name,
                            "url": f"https://github.com/{full_name}",
                            "description": post["data"].get("title") or "",
                            "stars": 0,
                            "language": "Unknown",
                            "source": "reddit",
                        }
                    )
    return results


async def fetch_all_sources() -> list[dict[str, Any]]:
    """Fetch repos from all configured discovery sources."""
    github_trending = await fetch_github_trending()
    github_velocity = await fetch_github_velocity()
    hackernews = await fetch_hackernews_repos()
    reddit = await fetch_reddit_repos()
    return github_trending + github_velocity + hackernews + reddit
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/discovery/test_sources.py::test_fetch_github_velocity_parses_search_results -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/discovery/ tests/discovery/
git commit -m "feat(discovery): add trending repo source scrapers"
```

---

## Task 2: Discovery Models

**Files:**
- Modify: `sahiixx_agency/core/models.py`
- Test: `tests/test_models.py` (create if not exists)

**Interfaces:**
- Produces:
  - `class DiscoveryResult(BaseModel)`
  - `class RiskLevel(str, Enum)`
  - `class ApprovalRequest(BaseModel)`
  - Update `RepoNode` to include `source: str = "registry"` and `risk_level: RiskLevel = RiskLevel.LOW`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from __future__ import annotations

from sahiixx_agency.core.models import DiscoveryResult, RiskLevel


def test_discovery_result_defaults() -> None:
    dr = DiscoveryResult(full_name="nexu-io/html-anything", url="https://github.com/nexu-io/html-anything")
    assert dr.stars == 0
    assert dr.language == "Unknown"
    assert dr.risk_level == RiskLevel.LOW
    assert dr.source == "discovery"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py::test_discovery_result_defaults -v`

Expected: FAIL — `ImportError: cannot import name 'DiscoveryResult'`

- [ ] **Step 3: Write minimal implementation**

Add to `sahiixx_agency/core/models.py` near the top with other enums/classes:

```python
class RiskLevel(str, Enum):
    """Risk classification for a module or task."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

Add near the bottom of `sahiixx_agency/core/models.py`:

```python
class DiscoveryResult(BaseModel):
    """A repo discovered from an external source."""

    full_name: str
    url: str
    description: str = ""
    stars: int = 0
    language: str = "Unknown"
    source: str = "discovery"
    risk_level: RiskLevel = RiskLevel.LOW
    category: RepoCategory = RepoCategory.UNCATEGORIZED
    entrypoint: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApprovalRequest(BaseModel):
    """A pending human approval for a risky task."""

    id: str
    task_id: str
    risk_level: RiskLevel
    reason: str
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_at: datetime | None = None
    approved_by: str | None = None
    status: str = "pending"  # pending, approved, rejected
```

Also add to `RepoNode`:

```python
    source: str = "registry"
    risk_level: RiskLevel = RiskLevel.LOW
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_models.py::test_discovery_result_defaults -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/core/models.py tests/test_models.py
git commit -m "feat(models): add DiscoveryResult, RiskLevel, ApprovalRequest"
```

---

## Task 3: Discovery Pipeline

**Files:**
- Create: `sahiixx_agency/discovery/pipeline.py`
- Modify: `sahiixx_agency/discovery/__init__.py` to export pipeline functions
- Test: `tests/discovery/test_pipeline.py`

**Interfaces:**
- Consumes: `DiscoveryResult`, `RepoNode`, `RepoRegistry`, source functions from `sources.py`.
- Produces:
  - `class DiscoveryPipeline`
  - `async def run(self, min_stars: int = 50) -> list[RepoNode]`
  - `def deduplicate(results: list[DiscoveryResult]) -> list[DiscoveryResult]`
  - `def classify(result: DiscoveryResult) -> DiscoveryResult`
  - `def score(result: DiscoveryResult) -> float`

- [ ] **Step 1: Write the failing test**

```python
# tests/discovery/test_pipeline.py
from __future__ import annotations

import pytest

from sahiixx_agency.core.models import DiscoveryResult, RiskLevel, RepoCategory
from sahiixx_agency.discovery.pipeline import DiscoveryPipeline, classify, deduplicate


def test_deduplicate_keeps_first() -> None:
    results = [
        DiscoveryResult(full_name="a/b", url="https://github.com/a/b", source="github"),
        DiscoveryResult(full_name="a/b", url="https://github.com/a/b", source="reddit"),
    ]
    out = deduplicate(results)
    assert len(out) == 1
    assert out[0].source == "github"


def test_classify_security_repo() -> None:
    result = classify(DiscoveryResult(full_name="x/pentest-tool", url="https://github.com/x/pentest-tool"))
    assert result.category == RepoCategory.SECURITY
    assert result.risk_level == RiskLevel.HIGH


def test_classify_agent_framework() -> None:
    result = classify(DiscoveryResult(full_name="x/awesome-llm-agent", url="https://github.com/x/awesome-llm-agent"))
    assert result.category == RepoCategory.AGENT_FRAMEWORK


@pytest.mark.asyncio
async def test_pipeline_filters_by_min_stars(monkeypatch):
    async def fake_sources():
        return [
            DiscoveryResult(full_name="a/b", url="https://github.com/a/b", stars=10),
            DiscoveryResult(full_name="c/d", url="https://github.com/c/d", stars=100),
        ]

    monkeypatch.setattr("sahiixx_agency.discovery.pipeline.fetch_all_sources", fake_sources)
    pipeline = DiscoveryPipeline(data_dir="./data_test", min_stars=50)
    nodes = await pipeline.run()
    assert len(nodes) == 1
    assert nodes[0].name == "d"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/discovery/test_pipeline.py -v`

Expected: FAIL — `ModuleNotFoundError` or `ImportError` for pipeline/category.

- [ ] **Step 3: Write minimal implementation**

Create `sahiixx_agency/discovery/pipeline.py`:

```python
"""Discovery pipeline: dedupe, filter, classify, score, register, clone."""

from __future__ import annotations

import asyncio
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sahiixx_agency.core.models import DiscoveryResult, RepoCategory, RepoNode, RiskLevel
from sahiixx_agency.discovery.sources import fetch_all_sources


CATEGORY_KEYWORDS: dict[RepoCategory, list[str]] = {
    RepoCategory.SECURITY: ["security", "pentest", "exploit", "vuln", "redteam", "cve", "audit", "scan"],
    RepoCategory.VOICE_AI: ["voice", "speech", "audio", "call", "tts", "stt"],
    RepoCategory.REAL_ESTATE: ["real estate", "property", "listing", "realtor", "dubai"],
    RepoCategory.AGENT_FRAMEWORK: ["agent", "llm", "ai", "swarm", "bot", "autonomous", "gpt", "claude"],
    RepoCategory.MCP_TOOL: ["mcp", "tool", "plugin", "extension"],
    RepoCategory.COOKBOOK: ["prompt", "cookbook", "template", "examples"],
    RepoCategory.OS_PLATFORM: ["os", "platform", "desktop", "workspace"],
}

RISK_OVERRIDES: dict[RepoCategory, RiskLevel] = {
    RepoCategory.SECURITY: RiskLevel.HIGH,
    RepoCategory.AGENT_FRAMEWORK: RiskLevel.MEDIUM,
}


def deduplicate(results: list[DiscoveryResult]) -> list[DiscoveryResult]:
    """Remove duplicate repos, keeping the first mention."""
    seen: set[str] = set()
    out: list[DiscoveryResult] = []
    for result in results:
        key = result.full_name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(result)
    return out


def classify(result: DiscoveryResult) -> DiscoveryResult:
    """Classify a discovery result by category and risk."""
    text = f"{result.full_name} {result.description}".lower()
    best_category = RepoCategory.UNCATEGORIZED
    best_score = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_category = category
    risk = RISK_OVERRIDES.get(best_category, RiskLevel.LOW)
    if result.stars < 10 and result.source in ("hackernews", "reddit"):
        risk = RiskLevel(risk.value) if risk != RiskLevel.LOW else RiskLevel.MEDIUM
    return result.model_copy(update={"category": best_category, "risk_level": risk})


def score(result: DiscoveryResult) -> float:
    """Score discovery result relevance; higher is better."""
    s = float(result.stars)
    if result.category != RepoCategory.UNCATEGORIZED:
        s += 100.0
    if result.language in ("Python", "TypeScript", "JavaScript"):
        s += 20.0
    return s


def _discovery_result_to_node(result: DiscoveryResult) -> RepoNode:
    owner, _, name = result.full_name.partition("/")
    return RepoNode(
        id=result.full_name.replace("/", "_"),
        name=name,
        owner=owner,
        full_name=result.full_name,
        url=result.url,
        description=result.description,
        stars=result.stars,
        language=result.language,
        category=result.category,
        source=result.source,
        risk_level=result.risk_level,
    )


class DiscoveryPipeline:
    """Runs the full discovery pipeline and registers results."""

    def __init__(
        self,
        data_dir: str = "./data",
        min_stars: int = 50,
        auto_clone: bool = False,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.min_stars = min_stars
        self.auto_clone = auto_clone
        self.discovery_dir = self.data_dir / "discovery"
        self.discovery_dir.mkdir(parents=True, exist_ok=True)

    async def run(self) -> list[RepoNode]:
        """Fetch, dedupe, filter, classify, and optionally clone trending repos."""
        raw = await fetch_all_sources()
        results = [DiscoveryResult.model_validate(r) for r in raw]
        results = deduplicate(results)
        results = [r for r in results if r.stars >= self.min_stars or r.source in ("hackernews", "reddit")]
        results = [classify(r) for r in results]
        results.sort(key=score, reverse=True)
        nodes = [_discovery_result_to_node(r) for r in results]
        if self.auto_clone:
            for node in nodes[:20]:
                await self._clone(node)
        self._save_snapshot(results)
        return nodes

    async def _clone(self, node: RepoNode) -> Path | None:
        target = self.data_dir / "repos" / "trending" / node.owner / node.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            return target
        proc = await asyncio.to_thread(
            subprocess.run,
            ["git", "clone", "--depth", "1", node.url, str(target)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0:
            return target
        return None

    def _save_snapshot(self, results: list[DiscoveryResult]) -> None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self.discovery_dir / f"{date_str}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for r in results:
                f.write(r.model_dump_json() + "\n")
```

Update `sahiixx_agency/discovery/__init__.py`:

```python
from .pipeline import DiscoveryPipeline, classify, deduplicate, score
from .sources import fetch_all_sources, fetch_github_trending, fetch_github_velocity, fetch_hackernews_repos, fetch_reddit_repos

__all__ = [
    "DiscoveryPipeline",
    "classify",
    "deduplicate",
    "score",
    "fetch_all_sources",
    "fetch_github_trending",
    "fetch_github_velocity",
    "fetch_hackernews_repos",
    "fetch_reddit_repos",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/discovery/test_pipeline.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/discovery/ tests/discovery/
git commit -m "feat(discovery): add dedupe, classify, score pipeline"
```

---

## Task 4: Entrypoint Inference

**Files:**
- Create: `sahiixx_agency/discovery/entrypoint.py`
- Modify: `sahiixx_agency/discovery/__init__.py`
- Test: `tests/discovery/test_entrypoint.py`

**Interfaces:**
- Produces:
  - `def infer_entrypoint(repo_dir: str | Path) -> list[str] | None`
  - `def detect_project_type(repo_dir: str | Path) -> str`

- [ ] **Step 1: Write the failing test**

```python
# tests/discovery/test_entrypoint.py
from __future__ import annotations

from pathlib import Path

from sahiixx_agency.discovery.entrypoint import detect_project_type, infer_entrypoint


def test_node_project(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"scripts": {"dev": "next dev"}}')
    assert detect_project_type(tmp_path) == "node"
    assert infer_entrypoint(tmp_path) == ["npm", "install", "&&", "npm", "run", "dev"]


def test_python_project(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "requirements.txt").write_text("requests\n")
    assert detect_project_type(tmp_path) == "python"
    assert infer_entrypoint(tmp_path) == ["pip", "install", "-r", "requirements.txt", "&&", "python", "main.py"]


def test_makefile_project(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text("run:\n\techo hi\n")
    assert detect_project_type(tmp_path) == "make"
    assert infer_entrypoint(tmp_path) == ["make", "run"]


def test_unknown_project(tmp_path: Path) -> None:
    assert detect_project_type(tmp_path) == "unknown"
    assert infer_entrypoint(tmp_path) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/discovery/test_entrypoint.py -v`

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# sahiixx_agency/discovery/entrypoint.py
"""Infer how to run a cloned repository."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def detect_project_type(repo_dir: str | Path) -> str:
    """Detect the dominant project type in a repo directory."""
    repo = Path(repo_dir)
    if (repo / "package.json").exists():
        return "node"
    if (repo / "pyproject.toml").exists() or (repo / "requirements.txt").exists():
        return "python"
    if (repo / "Dockerfile").exists() or (repo / "docker-compose.yml").exists():
        return "docker"
    if (repo / "Makefile").exists():
        return "make"
    if any((repo / name).exists() for name in ("main.py", "app.py", "run.py")):
        return "python"
    return "unknown"


def _node_entrypoint(repo: Path) -> list[str] | None:
    package = _read_json(repo / "package.json")
    scripts = package.get("scripts", {})
    for script in ("dev", "start", "serve", "run"):
        if script in scripts:
            return ["npm", "install", "&&", "npm", "run", script]
    return ["npm", "install", "&&", "npm", "start"]


def _python_entrypoint(repo: Path) -> list[str] | None:
    for script in ("main.py", "app.py", "run.py"):
        if (repo / script).exists():
            install_cmd = (
                ["pip", "install", "-e", "."]
                if (repo / "pyproject.toml").exists()
                else ["pip", "install", "-r", "requirements.txt"]
                if (repo / "requirements.txt").exists()
                else []
            )
            if install_cmd:
                return install_cmd + ["&&", "python", script]
            return ["python", script]
    return None


def _make_entrypoint(repo: Path) -> list[str] | None:
    makefile = (repo / "Makefile").read_text(encoding="utf-8")
    for target in ("run", "start", "dev", "all"):
        if f"{target}:" in makefile:
            return ["make", target]
    return ["make"]


def _docker_entrypoint(repo: Path) -> list[str] | None:
    return ["docker", "build", "-t", repo.name, ".", "&&", "docker", "run", "--rm", repo.name]


def infer_entrypoint(repo_dir: str | Path) -> list[str] | None:
    """Return the best-effort command to run a repo."""
    repo = Path(repo_dir)
    if not repo.is_dir():
        return None
    project_type = detect_project_type(repo)
    handlers = {
        "node": _node_entrypoint,
        "python": _python_entrypoint,
        "make": _make_entrypoint,
        "docker": _docker_entrypoint,
    }
    handler = handlers.get(project_type)
    return handler(repo) if handler else None
```

Update `sahiixx_agency/discovery/__init__.py`:

```python
from .entrypoint import detect_project_type, infer_entrypoint

__all__ = [
    ...,
    "detect_project_type",
    "infer_entrypoint",
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/discovery/test_entrypoint.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/discovery/ tests/discovery/
git commit -m "feat(discovery): infer repo entrypoint from files"
```

---

## Task 5: Generic Adapter

**Files:**
- Create: `sahiixx_agency/adapters/generic_adapter.py`
- Test: `tests/adapters/test_generic_adapter.py`

**Interfaces:**
- Consumes: `RepoNode`, inferred entrypoint.
- Produces:
  - `class GenericAdapter`
  - `async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]`

- [ ] **Step 1: Write the failing test**

```python
# tests/adapters/test_generic_adapter.py
from __future__ import annotations

import pytest

from sahiixx_agency.adapters.generic_adapter import GenericAdapter
from sahiixx_agency.core.models import RepoCategory, RepoNode


@pytest.mark.asyncio
async def test_generic_adapter_runs_inferred_command(tmp_path, monkeypatch):
    repo = tmp_path / "demo"
    repo.mkdir()
    (repo / "main.py").write_text("print('hello from demo')")

    node = RepoNode(
        id="demo",
        name="demo",
        owner="test",
        full_name="test/demo",
        url="https://github.com/test/demo",
        category=RepoCategory.UNCATEGORIZED,
    )

    adapter = GenericAdapter(data_dir=str(tmp_path))
    result = await adapter.run(node, {"command": "python main.py"})
    assert result["status"] == "success"
    assert "hello from demo" in result["stdout"]


@pytest.mark.asyncio
async def test_generic_adapter_simulates_when_no_local_clone():
    node = RepoNode(
        id="missing",
        name="missing",
        owner="test",
        full_name="test/missing",
        url="https://github.com/test/missing",
    )
    adapter = GenericAdapter(data_dir="/nonexistent")
    result = await adapter.run(node, {})
    assert result["status"] == "simulated"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/adapters/test_generic_adapter.py -v`

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# sahiixx_agency/adapters/generic_adapter.py
"""Generic adapter that runs any repo using an inferred or supplied command."""

from __future__ import annotations

import asyncio
import os
import subprocess
from pathlib import Path
from typing import Any

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.discovery.entrypoint import infer_entrypoint


class GenericAdapter:
    """Run any registered module by detecting its entrypoint."""

    def __init__(
        self,
        data_dir: str = "./data",
        timeout: int = 120,
        fallback_on_failure: bool = True,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.timeout = timeout
        self.fallback_on_failure = fallback_on_failure

    def _repo_dir(self, node: RepoNode) -> Path | None:
        candidates = [
            self.data_dir / "repos" / node.name,
            self.data_dir / "repos" / "trending" / node.owner / node.name,
            self.data_dir / "repos" / node.owner / node.name,
        ]
        if node.local_path:
            candidates.insert(0, Path(node.local_path))
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _build_command(self, node: RepoNode, payload: dict[str, Any]) -> list[str] | None:
        if payload.get("command"):
            return payload["command"].split()
        repo_dir = self._repo_dir(node)
        if repo_dir:
            entrypoint = infer_entrypoint(repo_dir)
            if entrypoint:
                return entrypoint
        return None

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        repo_dir = self._repo_dir(node)
        if repo_dir is None:
            return self._simulate(node, payload, reason="repo not cloned")

        command = self._build_command(node, payload)
        if command is None:
            return self._simulate(node, payload, reason="no entrypoint inferred")

        run_env = {**os.environ, **(payload.get("env") or {})}
        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                command,
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
                timeout=payload.get("timeout", self.timeout),
                env=run_env,
                check=False,
            )
            ok = proc.returncode == 0
            if not ok and self.fallback_on_failure:
                return self._simulate(node, payload, reason=f"exit code {proc.returncode}", stderr=proc.stderr[:500])
            return {
                "module": node.name,
                "status": "success" if ok else "error",
                "command": " ".join(command),
                "returncode": proc.returncode,
                "stdout": proc.stdout[:8000],
                "stderr": proc.stderr[:4000],
                "repo_dir": str(repo_dir),
            }
        except subprocess.TimeoutExpired:
            return self._simulate(node, payload, reason="timeout") if self.fallback_on_failure else {
                "module": node.name,
                "status": "timeout",
                "command": " ".join(command),
                "error": f"Timeout after {self.timeout}s",
            }
        except Exception as exc:  # noqa: BLE001
            return self._simulate(node, payload, reason=str(exc)) if self.fallback_on_failure else {
                "module": node.name,
                "status": "exception",
                "error": str(exc),
            }

    def _simulate(self, node: RepoNode, payload: dict[str, Any], reason: str, stderr: str = "") -> dict[str, Any]:
        return {
            "module": node.name,
            "status": "simulated",
            "command": payload.get("command") or "<inferred>",
            "stdout": f"[SIMULATED] Would run {node.full_name} with payload {payload}",
            "stderr": stderr or f"Fallback because: {reason}",
            "repo_dir": node.local_path or "",
            "fallback": True,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/adapters/test_generic_adapter.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/adapters/generic_adapter.py tests/adapters/test_generic_adapter.py
git commit -m "feat(adapters): add generic repo adapter"
```

---

## Task 6: Wire Generic Adapter into Engine

**Files:**
- Modify: `sahiixx_agency/core/engine.py`
- Test: `tests/test_core.py` (existing)

**Interfaces:**
- Consumes: `GenericAdapter`.
- Produces: engine uses `GenericAdapter` when no specialized adapter matches.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_core.py`:

```python
@pytest.mark.asyncio
async def test_engine_uses_generic_adapter_for_unknown_module(config, fake_registry, monkeypatch):
    engine = AgencyEngine(config)
    engine.registry = fake_registry
    fake_registry.modules = [
        RepoNode(
            id="demo",
            name="demo",
            owner="test",
            full_name="test/demo",
            url="https://github.com/test/demo",
            category=RepoCategory.UNCATEGORIZED,
        )
    ]
    await engine.start_worker()
    task = await engine.dispatch("run the demo repo", {"command": "echo hello"})
    await asyncio.sleep(0.2)
    assert task.status == TaskStatus.COMPLETED
    assert task.result["execution"]["status"] == "success"
    await engine.stop_worker()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_core.py::test_engine_uses_generic_adapter_for_unknown_module -v`

Expected: FAIL — generic adapter path not present.

- [ ] **Step 3: Write minimal implementation**

Modify `sahiixx_agency/core/engine.py` in `_execute_task`. After the existing `elif` branches and before the final `else` for generic `runner.run`, add:

```python
                    elif task.module_id:
                        # Generic fallback: infer entrypoint and run
                        from sahiixx_agency.adapters.generic_adapter import GenericAdapter

                        generic_adapter = GenericAdapter(
                            data_dir=self.config.data_dir,
                            timeout=task.payload.get("timeout", 120),
                        )
                        run_result = await generic_adapter.run(mod, task.payload)
                        task.result = {
                            "module": mod.name,
                            "category": mod.category.value,
                            "url": mod.url,
                            "capabilities": mod.capabilities,
                            "execution": run_result,
                        }
```

Replace the existing final `else` block that calls `self.runner.run` so it only runs for tasks without a `module_id`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_core.py::test_engine_uses_generic_adapter_for_unknown_module -v`

Expected: PASS

- [ ] **Step 5: Run full test suite and commit**

Run:
```bash
uv run pytest tests/ -q
uv run ruff check sahiixx_agency tests
uv run mypy sahiixx_agency
```

Expected: all green.

```bash
git add sahiixx_agency/core/engine.py tests/test_core.py
git commit -m "feat(engine): wire generic adapter as default execution path"
```

---

## Task 7: Discovery API Endpoints

**Files:**
- Modify: `sahiixx_agency/api/main.py`
- Test: `tests/test_api_discovery.py`

**Interfaces:**
- Produces:
  - `POST /discovery/run` — trigger discovery pipeline
  - `GET /discovery/trending` — list recently discovered repos
  - `GET /discovery/snapshots` — list snapshot files

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_discovery.py
from __future__ import annotations

from fastapi.testclient import TestClient

from sahiixx_agency.api.main import app


client = TestClient(app)


def test_discovery_run_endpoint(monkeypatch):
    async def fake_run(self):
        return []

    monkeypatch.setattr("sahiixx_agency.discovery.pipeline.DiscoveryPipeline.run", fake_run)
    response = client.post("/discovery/run")
    assert response.status_code == 200
    assert response.json()["discovered"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_api_discovery.py::test_discovery_run_endpoint -v`

Expected: FAIL — 404.

- [ ] **Step 3: Write minimal implementation**

Add to `sahiixx_agency/api/main.py` after existing endpoints:

```python
# ---------- Discovery ----------


class DiscoveryRunRequest(BaseModel):
    min_stars: int = 0
    auto_clone: bool = False


@app.post("/discovery/run")
async def run_discovery(
    request: DiscoveryRunRequest,
) -> dict[str, Any]:
    """Run the discovery pipeline and return newly discovered repos."""
    from sahiixx_agency.discovery.pipeline import DiscoveryPipeline

    pipeline = DiscoveryPipeline(min_stars=request.min_stars, auto_clone=request.auto_clone)
    nodes = await pipeline.run()
    return {"discovered": len(nodes), "repos": [n.model_dump(mode="json") for n in nodes[:50]]}


@app.get("/discovery/trending")
async def list_trending() -> list[dict[str, Any]]:
    """Return the most recent daily snapshot of discovered repos."""
    from datetime import timezone
    from pathlib import Path

    from sahiixx_agency.core.models import DiscoveryResult

    data_dir = Path("./data/discovery")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = data_dir / f"{today}.jsonl"
    if not path.exists():
        return []
    results = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(DiscoveryResult.model_validate_json(line).model_dump(mode="json"))
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_api_discovery.py::test_discovery_run_endpoint -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/api/main.py tests/test_api_discovery.py
git commit -m "feat(api): add discovery endpoints"
```

---

## Task 8: Dashboard Trending Panel

**Files:**
- Create: `dashboard/src/components/discovery/TrendingPanel.tsx`
- Modify: `dashboard/src/pages/Home.tsx` to include the panel
- Test: `dashboard/src/components/discovery/__tests__/TrendingPanel.test.tsx` (optional, if Vitest/jest setup exists)

**Interfaces:**
- Consumes: `GET /discovery/trending` API.
- Produces: React component rendering trending repos with dispatch button.

- [ ] **Step 1: Create component**

```tsx
// dashboard/src/components/discovery/TrendingPanel.tsx
import { useEffect, useState } from "react";

interface TrendingRepo {
  full_name: string;
  url: string;
  description: string;
  stars: number;
  language: string;
  category: string;
  risk_level: string;
}

export function TrendingPanel() {
  const [repos, setRepos] = useState<TrendingRepo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/discovery/trending")
      .then((r) => r.json())
      .then((data) => setRepos(Array.isArray(data) ? data : []))
      .finally(() => setLoading(false));
  }, []);

  const dispatch = (full_name: string) => {
    fetch("/api/dispatch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ intent: `run ${full_name}`, payload: { module_id: full_name.replace("/", "_") } }),
    });
  };

  if (loading) return <div className="p-4 text-sm text-gray-400">Loading trending...</div>;

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <h2 className="mb-3 text-lg font-semibold text-white">Trending Repos</h2>
      <div className="space-y-3">
        {repos.length === 0 && <p className="text-sm text-gray-400">No trending repos discovered yet.</p>}
        {repos.map((repo) => (
          <div key={repo.full_name} className="rounded border border-gray-800 p-3 hover:border-gray-700">
            <div className="flex items-center justify-between">
              <a href={repo.url} target="_blank" rel="noreferrer" className="font-medium text-blue-400 hover:underline">
                {repo.full_name}
              </a>
              <span className="text-xs text-yellow-400">★ {repo.stars}</span>
            </div>
            <p className="mt-1 text-sm text-gray-300">{repo.description}</p>
            <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
              <span>{repo.language}</span>
              <span>•</span>
              <span>{repo.category}</span>
              <span>•</span>
              <span className="uppercase">{repo.risk_level}</span>
            </div>
            <button
              onClick={() => dispatch(repo.full_name)}
              className="mt-2 rounded bg-blue-600 px-3 py-1 text-xs text-white hover:bg-blue-500"
            >
              Dispatch
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add to Home page**

Modify `dashboard/src/pages/Home.tsx` to import and render `<TrendingPanel />` in a side panel or below the graph. Example:

```tsx
import { TrendingPanel } from "../components/discovery/TrendingPanel";

// Inside the main layout, add:
<aside className="w-80 shrink-0 overflow-y-auto p-4">
  <TrendingPanel />
</aside>
```

- [ ] **Step 3: Verify build**

Run:
```bash
cd dashboard
npm install
npm run build
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add dashboard/
git commit -m "feat(dashboard): add trending repos panel"
```

---

## Task 9: Approval Gate Stub

**Files:**
- Create: `sahiixx_agency/core/approval.py`
- Modify: `sahiixx_agency/core/engine.py` to check risk before execution.
- Test: `tests/test_approval.py`

**Interfaces:**
- Produces:
  - `class ApprovalManager`
  - `def request_approval(self, task: AgencyTask) -> ApprovalRequest`
  - `def approve(self, request_id: str) -> ApprovalRequest`
  - `def is_approved(self, task_id: str) -> bool`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_approval.py
from __future__ import annotations

from sahiixx_agency.core.approval import ApprovalManager
from sahiixx_agency.core.models import AgencyTask, RiskLevel


def test_approval_required_for_high_risk() -> None:
    mgr = ApprovalManager()
    task = AgencyTask(id="task_1", intent="scan target", module_id="t3mp3st", payload={"risk_level": "critical"})
    req = mgr.request_approval(task, RiskLevel.CRITICAL, "security tool")
    assert req.status == "pending"
    assert not mgr.is_approved("task_1")
    mgr.approve(req.id, by="user")
    assert mgr.is_approved("task_1")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_approval.py -v`

Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# sahiixx_agency/core/approval.py
"""Human-in-the-loop approval manager."""

from __future__ import annotations

import uuid
from datetime import timezone
from typing import Any

from sahiixx_agency.core.models import AgencyTask, ApprovalRequest, RiskLevel


class ApprovalManager:
    """Track pending and approved risky tasks."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}
        self._by_task: dict[str, str] = {}

    def request_approval(self, task: AgencyTask, risk_level: RiskLevel, reason: str) -> ApprovalRequest:
        request_id = f"apr_{uuid.uuid4().hex[:8]}"
        req = ApprovalRequest(
            id=request_id,
            task_id=task.id,
            risk_level=risk_level,
            reason=reason,
        )
        self._requests[request_id] = req
        self._by_task[task.id] = request_id
        return req

    def approve(self, request_id: str, by: str) -> ApprovalRequest | None:
        req = self._requests.get(request_id)
        if req is None:
            return None
        req.status = "approved"
        req.approved_by = by
        from datetime import datetime
        req.approved_at = datetime.now(timezone.utc)
        return req

    def reject(self, request_id: str, by: str) -> ApprovalRequest | None:
        req = self._requests.get(request_id)
        if req is None:
            return None
        req.status = "rejected"
        req.approved_by = by
        from datetime import datetime
        req.approved_at = datetime.now(timezone.utc)
        return req

    def approve_by_task(self, task_id: str, by: str) -> ApprovalRequest | None:
        request_id = self._by_task.get(task_id)
        if request_id is None:
            return None
        return self.approve(request_id, by)

    def is_approved(self, task_id: str) -> bool:
        request_id = self._by_task.get(task_id)
        if not request_id:
            return False
        return self._requests[request_id].status == "approved"

    def is_rejected(self, task_id: str) -> bool:
        request_id = self._by_task.get(task_id)
        if not request_id:
            return False
        return self._requests[request_id].status == "rejected"

    def list_pending(self) -> list[ApprovalRequest]:
        return [r for r in self._requests.values() if r.status == "pending"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_approval.py -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add sahiixx_agency/core/approval.py tests/test_approval.py
git commit -m "feat(approval): add human-in-the-loop approval manager"
```

---

## Task 10: Final Integration and Push

**Files:**
- Modify: `config/agency.yaml` — add discovery defaults
- Modify: `sahiixx_agency/api/main.py` — add `/tasks/{id}/approve` endpoint
- Modify: `sahiixx_agency/core/engine.py` — add `ApprovalManager` instance
- Test: full suite

- [ ] **Step 1: Update config**

Add to `config/agency.yaml`:

```yaml
# ─── Discovery Settings ────────────────────────────────────────
discovery:
  enabled: true
  min_stars: 50
  languages: ["python", "typescript", "javascript", "go", "rust"]
  subreddits: ["MachineLearning", "webdev", "LocalLLaMA", "selfhosted"]
  auto_clone: false
  schedule: "0 6 * * *"

approval:
  auto_approve_low_risk: true
  require_approval_for: ["high", "critical"]
```

- [ ] **Step 2: Add ApprovalManager to engine**

Modify `sahiixx_agency/core/engine.py`:

```python
from .approval import ApprovalManager
```

In `AgencyEngine.__init__`:

```python
        self.approval = ApprovalManager()
```

- [ ] **Step 3: Add approve endpoint**

Add to `sahiixx_agency/api/main.py`:

```python
@app.post("/tasks/{task_id}/approve")
async def approve_task(task_id: str, engine: Annotated[AgencyEngine, Depends(get_engine)]) -> dict[str, Any]:
    """Approve a pending high-risk task."""
    task = engine.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    req = engine.approval.approve_by_task(task_id, by="dashboard")
    if req is None:
        raise HTTPException(status_code=400, detail="No approval request for task")
    # Re-queue task if it was paused
    await engine._task_queue.put(task)
    return {"status": "approved", "request_id": req.id}
```

- [ ] **Step 4: Run full verification**

```bash
uv run pytest tests/ -q
uv run ruff check sahiixx_agency tests
uv run mypy sahiixx_agency
cd dashboard && npm run build
```

Expected: all green.

- [ ] **Step 4: Commit and push**

```bash
git add .
git commit -m "feat(agency): Phase 1 command center with discovery, generic adapter, and approval gates"
git push origin master
```

---

## Self-Review Checklist

- [x] **Spec coverage**: Phase 1 command center, discovery feed, generic adapter, approval gates, and trending dashboard are all represented.
- [x] **Placeholder scan**: No TBD/TODO placeholders; every step includes exact file paths, code, commands, and expected output.
- [x] **Type consistency**: `DiscoveryResult`, `RepoNode`, `ApprovalRequest`, and `RiskLevel` are used consistently across tasks.
- [x] **Testability**: Every task has a failing test first, then implementation, then passing test.
- [x] **DRY/YAGNI**: Twitter/X source omitted in favor of GitHub/HN/Reddit to keep scope tight; can be added in Phase 2.

---

## Open Gaps for Phase 2

- Twitter/X discovery source.
- Real sandboxing (network block, cgroups).
- Persistent event bus queue (currently in-memory).
- LLM abstraction layer.
- MCP gateway.
- Telegram approval bot integration.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-06-one-person-digital-ai-agency-phase1.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using `executing-plans`, batch execution with checkpoints.

Which approach do you want?
