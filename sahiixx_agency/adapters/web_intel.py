"""Web intelligence adapter: fetch and analyze public web pages and GitHub profiles."""

from __future__ import annotations

import re
from typing import Any

import httpx

from sahiixx_agency.adapters.base import BaseAdapter


class WebIntelAdapter(BaseAdapter):
    """Fetch a URL and extract structured information.

    Special handling for GitHub profile/README pages. Returns a result dict
    with extracted headings, project names, descriptions, and links.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = payload.get("url") or payload.get("brief", "").strip()
        if not url:
            return {"status": "failed", "error": "No URL provided"}

        if not url.startswith("http"):
            url = f"https://{url}"

        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "OPA-WebIntel/1.0"})
                resp.raise_for_status()
                html = resp.text
        except Exception as exc:  # noqa: BLE001
            return {"status": "failed", "error": f"Fetch failed: {exc}"}

        text = self._strip_html(html)
        extracted = self._extract_projects(html)
        return {
            "status": "success",
            "url": url,
            "title": self._extract_title(html),
            "projects": extracted,
            "summary": self._summarize(text),
        }

    def _strip_html(self, html: str) -> str:
        text = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL)
        text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _extract_title(self, html: str) -> str:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else ""

    def _extract_projects(self, html: str) -> list[dict[str, str]]:
        """Heuristic extraction of project names and descriptions from HTML.

        Looks for common GitHub profile README patterns such as:
        - **project-name** description
        - <strong>name</strong> description
        - ### 🚀 Project Name<br>Description
        """
        projects: list[dict[str, str]] = []
        # Pattern: **name** description (raw markdown embedded in HTML)
        for m in re.finditer(r"\*\*([a-zA-Z0-9_\-]+)\*\*[:\s]+([^*\n]{5,120})", html):
            projects.append({"name": m.group(1), "description": m.group(2).strip()})
        # Pattern: <strong>name</strong> description
        for m in re.finditer(r"<strong[^>]*>([a-zA-Z0-9_\-]+)</strong>[:\s]+([^<\n]{5,120})", html, flags=re.IGNORECASE):
            projects.append({"name": m.group(1), "description": m.group(2).strip()})
        # Pattern: ### 🚀 Name<br>Description
        for m in re.finditer(r"###\s*[🚀🤖🏠🎙️🔒]\s*([^<]+)<br>([^<]{10,200})", html):
            projects.append({"name": m.group(1).strip(), "description": m.group(2).strip()})
        # Deduplicate by name, keep first
        seen: set[str] = set()
        unique: list[dict[str, str]] = []
        for p in projects:
            if p["name"] not in seen:
                seen.add(p["name"])
                unique.append(p)
        return unique[:30]

    def _summarize(self, text: str) -> str:
        return text[:800]
