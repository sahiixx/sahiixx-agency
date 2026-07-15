"""Discovery adapter: routes discovery/intel intents to the GitHub trending scout.

Unlike repo-based adapters, this adapter runs in-process via ``execute()`` and
queries the GitHub search API for trending / hidden-gem repositories. It mirrors
the logic of ``AgencyEngine.run_intel_scout`` so that natural-language intents
like "find trending AI agent repos" or "discover new github projects" resolve to
a real, dispatchable module instead of falling through keyword scoring to an
unrelated agent.

Payload options:
    report_type: "trending" (default), "velocity", or "hidden_gems"
    min_stars:   int, default 50
    languages:   list[str], optional language filters
    github_token: optional token to raise the GitHub rate limit
    simulate:    if True, skip the network call and return a deterministic sample
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


class DiscoveryAdapter:
    """In-process adapter that surfaces trending GitHub repositories."""

    def __init__(
        self,
        github_token: str | None = None,
        timeout: int = 30,
    ) -> None:
        self.github_token = github_token
        self.timeout = timeout

    def _simulate(self, report_type: str, min_stars: int) -> dict[str, Any]:
        """Deterministic fallback when the network/API is unavailable."""
        sample = [
            {"name": "sample-agent-framework", "owner": "octocat", "stars": 1200, "language": "Python"},
            {"name": "trending-rag-toolkit", "owner": "octocat", "stars": 860, "language": "TypeScript"},
            {"name": "hidden-gem-orchestrator", "owner": "octocat", "stars": 340, "language": "Rust"},
        ]
        return {
            "status": "simulated",
            "report_type": report_type,
            "min_stars": min_stars,
            "repos_found": len(sample),
            "repos": sample,
            "note": "GitHub API unavailable or simulate=True; returning sample discovery set.",
        }

    async def _search(self, query: str, per_page: int) -> list[dict[str, Any]]:
        import httpx

        headers = {"Accept": "application/vnd.github+json", "User-Agent": "sahiixx-agency"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        url = (
            "https://api.github.com/search/repositories"
            f"?q={query}&sort=stars&order=desc&per_page={per_page}"
        )
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(f"GitHub search returned HTTP {resp.status_code}")
            data = resp.json()
        return data.get("items", [])

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run a discovery scout and return a normalized report."""
        report_type = str(payload.get("report_type", "trending"))
        min_stars = int(payload.get("min_stars", 50))
        languages = payload.get("languages") or []

        if payload.get("simulate"):
            return self._simulate(report_type, min_stars)

        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        try:
            if report_type == "hidden_gems":
                query = f"stars:100..1000 pushed:>{week_ago}"
                items = await self._search(query, per_page=15)
            else:  # trending / velocity
                query = f"created:>{week_ago} stars:>{min_stars}"
                if languages:
                    query += " language:" + " language:".join(languages)
                items = await self._search(query, per_page=20)
        except Exception as exc:  # noqa: BLE001 - graceful fallback on any network/API error
            result = self._simulate(report_type, min_stars)
            result["status"] = "fallback"
            result["error"] = str(exc)[:300]
            return result

        repos = [
            {
                "name": item.get("name"),
                "owner": (item.get("owner") or {}).get("login"),
                "stars": item.get("stargazers_count"),
                "language": item.get("language"),
                "url": item.get("html_url"),
                "description": (item.get("description") or "")[:200],
            }
            for item in items
        ]
        return {
            "status": "success",
            "report_type": report_type,
            "min_stars": min_stars,
            "query": query,
            "repos_found": len(repos),
            "repos": repos,
        }
