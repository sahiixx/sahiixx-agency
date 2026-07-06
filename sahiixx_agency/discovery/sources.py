"""Fetch trending repos from GitHub, Hacker News, Reddit, and X."""

from __future__ import annotations

import os
import re
from typing import Any

import httpx

_GITHUB_API = "https://api.github.com"
_HN_API = "http://hn.algolia.com/api/v1"


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "sahiixx-agency-discovery"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _repo_url_to_full_name(url: str) -> str | None:
    match = re.search(r"github\.com/([^/]+/[^/]+)", url)
    if match:
        return match.group(1).rstrip("/")
    return None


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
    url = f"{_GITHUB_API}/search/repositories?q={q}&per_page=20"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=_headers())
    if resp.status_code != 200:
        return []
    return [_item_to_result(item, "github_trending") for item in resp.json().get("items", [])]


async def fetch_github_velocity(
    languages: list[str] | None = None,
    min_stars: int = 50,
) -> list[dict[str, Any]]:
    """Fetch recently starred repos."""
    languages = languages or ["python"]
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=30) as client:
        for language in languages:
            q = f"created:>7d stars:>{min_stars} language:{language} sort:stars"
            url = f"{_GITHUB_API}/search/repositories?q={q}&per_page=10"
            resp = await client.get(url, headers=_headers())
            if resp.status_code == 200:
                results.extend(_item_to_result(item, "github_velocity") for item in resp.json().get("items", []))
    return results


async def fetch_hackernews_repos() -> list[dict[str, Any]]:
    """Fetch Show HN stories and extract GitHub URLs."""
    url = f"{_HN_API}/search?tags=show_hn&hitsPerPage=30"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
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


async def fetch_all_sources(
    languages: list[str] | None = None,
    subreddits: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch repos from all configured discovery sources."""
    github_trending = await fetch_github_trending()
    github_velocity = await fetch_github_velocity(languages=languages)
    hackernews = await fetch_hackernews_repos()
    reddit = await fetch_reddit_repos(subreddits=subreddits)
    return github_trending + github_velocity + hackernews + reddit
