"""Discovery feed for trending repos."""

from __future__ import annotations

from .entrypoint import detect_project_type, infer_entrypoint
from .pipeline import DiscoveryPipeline, classify, deduplicate, score
from .sources import (
    fetch_all_sources,
    fetch_github_trending,
    fetch_github_velocity,
    fetch_hackernews_repos,
    fetch_reddit_repos,
)

__all__ = [
    "detect_project_type",
    "infer_entrypoint",
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
