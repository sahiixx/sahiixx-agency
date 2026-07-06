"""Discovery feed for trending repos."""

from __future__ import annotations

from .sources import (
    fetch_all_sources,
    fetch_github_trending,
    fetch_github_velocity,
    fetch_hackernews_repos,
    fetch_reddit_repos,
)

__all__ = [
    "fetch_all_sources",
    "fetch_github_trending",
    "fetch_github_velocity",
    "fetch_hackernews_repos",
    "fetch_reddit_repos",
]
