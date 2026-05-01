"""GitHub repo auto-discovery and agency module registry."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from .models import ModuleStatus, RepoCategory, RepoNode


# Keywords → category mapping
CATEGORY_RULES: list[tuple[RepoCategory, list[str]]] = [
    (
        RepoCategory.AGENT_FRAMEWORK,
        [
            "agent",
            "agency",
            "swarm",
            "hermes",
            "coral",
            "goose",
            "autogen",
            "openai",
            "claude",
            "llm",
            "langchain",
            "crew",
            "bot",
            "multi-agent",
            "orchestrat",
        ],
    ),
    (
        RepoCategory.VOICE_AI,
        [
            "voice",
            "jarvis",
            "speech",
            "audio",
            "tts",
            "stt",
            "whisper",
            "talk",
            "call",
            "phone",
        ],
    ),
    (
        RepoCategory.REAL_ESTATE,
        [
            "real estate",
            "property",
            "dubai",
            "realtor",
            "deal",
            "lead",
            "crm",
        ],
    ),
    (
        RepoCategory.SECURITY,
        [
            "security",
            "cve",
            "pentest",
            "audit",
            "vuln",
            "hack",
            "recon",
            "osint",
        ],
    ),
    (
        RepoCategory.MCP_TOOL,
        [
            "mcp",
            "tool",
            "plugin",
            "extension",
            "n8n",
            "workflow",
            "automation",
        ],
    ),
    (
        RepoCategory.COOKBOOK,
        [
            "prompt",
            "cookbook",
            "awesome",
            "system-prompt",
            "template",
            "guide",
        ],
    ),
    (
        RepoCategory.OS_PLATFORM,
        [
            "os",
            "platform",
            "workspace",
            "desktop",
            "shell",
            "terminal",
            "infra",
            "gateway",
        ],
    ),
    (
        RepoCategory.INFRASTRUCTURE,
        [
            "docker",
            "deploy",
            "api",
            "gateway",
            "server",
            "cloud",
            "kubernetes",
            "terraform",
        ],
    ),
]


def _classify_repo(name: str, description: str | None, topics: list[str]) -> RepoCategory:
    """Classify a repo into a category."""
    text = f"{name} {description or ''} {' '.join(topics)}".lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in text for kw in keywords):
            return category
    return RepoCategory.UNCATEGORIZED


class RepoRegistry:
    """Maintains the registry of all agency modules (repos)."""

    def __init__(self, data_dir: str = "./data", github_token: str | None = None) -> None:
        self.data_dir = data_dir
        self.github_token = github_token
        self.registry_path = os.path.join(data_dir, "registry.json")
        self._modules: dict[str, RepoNode] = {}
        os.makedirs(data_dir, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.registry_path):
            with open(self.registry_path, encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("modules", []):
                node = RepoNode.model_validate(item)
                self._modules[node.id] = node

    def _save(self) -> None:
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "module_count": len(self._modules),
            "modules": [m.model_dump(mode="json") for m in self._modules.values()],
        }
        with open(self.registry_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)

    @property
    def modules(self) -> list[RepoNode]:
        return list(self._modules.values())

    def get(self, module_id: str) -> RepoNode | None:
        return self._modules.get(module_id)

    def by_category(self, category: RepoCategory) -> list[RepoNode]:
        return [m for m in self._modules.values() if m.category == category]

    async def discover(self, username: str = "sahiixx", per_page: int = 100) -> list[RepoNode]:
        """Fetch all public repos for a GitHub user and register them."""
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "sahiixx-agency"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"

        discovered: list[RepoNode] = []
        async with httpx.AsyncClient(timeout=30) as client:
            page = 1
            while True:
                url = (
                    f"https://api.github.com/users/{username}/repos"
                    f"?per_page={per_page}&page={page}&sort=updated&direction=desc"
                )
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                batch = resp.json()
                if not batch:
                    break
                for raw in batch:
                    node = self._raw_to_node(raw)
                    discovered.append(node)
                    self._modules[node.id] = node
                if len(batch) < per_page:
                    break
                page += 1

        self._save()
        return discovered

    def _raw_to_node(self, raw: dict[str, Any]) -> RepoNode:
        name = raw["name"]
        desc = raw.get("description") or ""
        topics = raw.get("topics", [])
        category = _classify_repo(name, desc, topics)

        # Infer capabilities from name/description/topics
        capabilities: list[str] = []
        cap_keywords = {
            "scrape": ["scrape", "crawl", "fetch"],
            "analyze": ["analyze", "audit", "scan"],
            "generate": ["generate", "create", "build"],
            "chat": ["chat", "converse", "dialog"],
            "voice": ["voice", "speech", "audio"],
            "deploy": ["deploy", "docker", "kubernetes"],
            "monitor": ["monitor", "watch", "track"],
            "transform": ["transform", "convert", "translate"],
        }
        full_text = f"{name} {desc} {' '.join(topics)}".lower()
        for cap, kws in cap_keywords.items():
            if any(kw in full_text for kw in kws):
                capabilities.append(cap)

        return RepoNode(
            id=name,
            name=name,
            owner=raw["owner"]["login"],
            full_name=raw["full_name"],
            description=desc,
            url=raw["html_url"],
            clone_url=raw.get("clone_url"),
            category=category,
            language=raw.get("language"),
            stars=raw.get("stargazers_count", 0),
            forks=raw.get("forks_count", 0),
            is_fork=raw.get("fork", False),
            is_private=raw.get("private", False),
            topics=topics,
            updated_at=self._parse_iso(raw.get("updated_at")),
            created_at=self._parse_iso(raw.get("created_at")),
            pushed_at=self._parse_iso(raw.get("pushed_at")),
            status=ModuleStatus.REGISTERED,
            capabilities=list(set(capabilities)),
            manifest={"raw": raw},
        )

    @staticmethod
    def _parse_iso(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    def set_status(self, module_id: str, status: ModuleStatus) -> None:
        if module_id in self._modules:
            self._modules[module_id].status = status
            self._save()

    def update_manifest(self, module_id: str, manifest: dict[str, Any]) -> None:
        if module_id in self._modules:
            self._modules[module_id].manifest.update(manifest)
            self._save()

    def stats(self) -> dict[str, Any]:
        from collections import Counter

        cats = Counter(m.category for m in self._modules.values())
        langs = Counter(m.language for m in self._modules.values() if m.language)
        total_stars = sum(m.stars for m in self._modules.values())
        return {
            "total_modules": len(self._modules),
            "total_stars": total_stars,
            "by_category": dict(cats),
            "by_language": dict(langs),
            "active": sum(1 for m in self._modules.values() if m.status == ModuleStatus.ACTIVE),
        }
