"""Promote GitHub starred repos into OPA ecosystem modules.

Turns a list of starred repositories into ecosystem stubs + routing rules so the
manual curation done in ``docs/ecosystem-candidates.md`` becomes a one-command
refresh. Network IO is opt-in (fetch) and the CLI defaults to a dry-run that only
prints the proposed YAML; ``--write`` appends to ``config/agency.yaml``.
"""

from __future__ import annotations

import os
import re
from typing import Any

import httpx
import yaml

_GITHUB_API = "https://api.github.com"

# Ordered category detection. First match wins, so put specific categories first.
_CATEGORY_KEYWORDS: list[tuple[str, list[str]]] = [
    ("security", ["security", "pentest", "secret", "vuln", "red.team", "exploit", "scan", "cve"]),
    ("mcp", ["model context protocol", "mcp server", "devtools mcp", "mcp"]),
    ("extraction", ["pdf", "document", "miner", "markdown", "ocr", "docx"]),
    ("scraper", ["scrap", "crawl", "fetch website", "web crawler"]),
    ("realestate", ["real.estate", "property", "listing", "geo", "dubai"]),
    ("career", ["job", "career", "resume", "cv", "hiring", "linkedin", "recruit"]),
    ("knowledge", ["obsidian", "vault", "wiki", "second.brain", "notes"]),
    ("voice", ["voice", "speech", "tts", "stt", "phone", "call"]),
    ("design", ["design", "landing.page", "prototype", "figma", "ui kit"]),
    ("content_media", ["video", "audio", "image", "social", "youtube", "montage", "thumbnail"]),
    ("automation", ["workflow", "automation", "n8n", "integration", "zapier"]),
    ("model", ["local llm", "inference", "ollama", "vllm", "stable-diffusion", "diffusion"]),
    ("framework", ["agent framework", "multi-agent", "orchestrat", "rag", "langchain", "crew", "autogen"]),
    ("agent", ["coding agent", "cli agent", "ai agent", "assistant", "operator"]),
]

_CATEGORY_META: dict[str, dict[str, str]] = {
    "framework": {"bus": "framework.*", "protocol": "python-lib"},
    "agent": {"bus": "agent.*", "protocol": "subprocess"},
    "security": {"bus": "security.*", "protocol": "subprocess"},
    "mcp": {"bus": "mcp.*", "protocol": "mcp"},
    "extraction": {"bus": "extraction.*", "protocol": "subprocess"},
    "scraper": {"bus": "scraper.*", "protocol": "subprocess"},
    "realestate": {"bus": "realestate.*", "protocol": "rest"},
    "career": {"bus": "career.*", "protocol": "python-lib"},
    "knowledge": {"bus": "knowledge.*", "protocol": "subprocess"},
    "voice": {"bus": "voice.*", "protocol": "api"},
    "design": {"bus": "design.*", "protocol": "api"},
    "content_media": {"bus": "content_media.*", "protocol": "subprocess"},
    "automation": {"bus": "automation.*", "protocol": "api"},
    "model": {"bus": "model.*", "protocol": "api"},
}


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "sahiixx-agency-discovery"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def slugify(name: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return key or "module"


def classify_category(repo: dict[str, Any]) -> str:
    text = f"{repo.get('full_name', '')} {repo.get('description', '')}".lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        if any(kw in text for kw in keywords):
            return category
    return "framework"


def build_ecosystem_entry(repo: dict[str, Any], category: str | None = None) -> tuple[str, dict[str, Any]]:
    full_name = repo.get("full_name") or f"{repo.get('owner')}/{repo.get('name')}"
    owner, _, name = full_name.partition("/")
    key = slugify(name)
    category = category or classify_category(repo)
    meta = _CATEGORY_META.get(category, _CATEGORY_META["framework"])
    role = (repo.get("description") or f"Promoted starred repo {full_name}").strip()
    return key, {
        "repo": name,
        "owner": owner or "sahiixx",
        "url": repo.get("html_url") or f"https://github.com/{full_name}",
        "role": role,
        "bus_channel": meta["bus"],
        "protocol": meta["protocol"],
        "priority": 2,
        "tags": [category, name],
    }


def build_routing_rule(key: str, repo: dict[str, Any]) -> dict[str, str]:
    """Build a YAML/regex-safe routing pattern from the repo name.

    Repo names only contain ``[a-zA-Z0-9._-]``; the only regex metacharacter
    among those is ``.`` which harmlessly matches any character. We deliberately
    do NOT escape, because backslashes are invalid inside YAML double-quoted
    scalars (the format used for routing rules).
    """
    full_name = repo.get("full_name") or ""
    owner, _, name = full_name.partition("/")
    pattern = f"{name}|{full_name}"
    return {"pattern": pattern, "target": key}


async def fetch_stars(
    username: str,
    token: str | None = None,
    per_page: int = 100,
    max_pages: int = 5,
) -> list[dict[str, Any]]:
    """Fetch starred repos for a GitHub user.

    Returns a normalized list with keys: full_name, name, owner, html_url,
    description. Returns an empty list on any transport error so callers stay
    offline-safe.
    """
    results: list[dict[str, Any]] = []
    headers = _headers()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            for page in range(1, max_pages + 1):
                resp = await client.get(
                    f"{_GITHUB_API}/users/{username}/starred",
                    headers=headers,
                    params={"per_page": per_page, "page": page},
                )
                if resp.status_code != 200:
                    break
                items = resp.json()
                if not items:
                    break
                for item in items:
                    full = item.get("full_name", "")
                    owner, _, name = full.partition("/")
                    results.append(
                        {
                            "full_name": full,
                            "name": name,
                            "owner": owner,
                            "html_url": item.get("html_url", ""),
                            "description": item.get("description") or "",
                        }
                    )
                if len(items) < per_page:
                    break
    except Exception:  # noqa: BLE001 - offline-safe: never raise on network issues
        return []
    return results


def generate_promotions(
    stars: list[dict[str, Any]],
    existing_keys: set[str],
    existing_targets: set[str],
) -> dict[str, Any]:
    """Produce new ecosystem stubs + routing rules for stars not yet promoted."""
    ecosystem: dict[str, Any] = {}
    routing_rules: list[dict[str, str]] = []
    for repo in stars:
        key, entry = build_ecosystem_entry(repo)
        if key in existing_keys or key in ecosystem:
            continue
        ecosystem[key] = entry
        rule = build_routing_rule(key, repo)
        if rule["target"] not in existing_targets:
            routing_rules.append(rule)
        existing_keys.add(key)
        existing_targets.add(key)
    return {"ecosystem": ecosystem, "routing_rules": routing_rules}


def render_yaml(additions: dict[str, Any]) -> str:
    """Render the proposed additions as a YAML snippet (dry-run output)."""
    lines: list[str] = ["# ── Promoted from GitHub stars ──"]
    for key, entry in additions["ecosystem"].items():
        lines.append(f"{key}:")
        lines.append(f'  repo: {entry["repo"]}')
        lines.append(f'  owner: {entry["owner"]}')
        lines.append(f'  url: {entry["url"]}')
        lines.append(f'  role: "{entry["role"]}"')
        lines.append(f'  bus_channel: "{entry["bus_channel"]}"')
        lines.append(f'  protocol: {entry["protocol"]}')
        lines.append("  priority: 2")
        tags = ", ".join(entry["tags"])
        lines.append(f"  tags: [{tags}]")
    if additions["routing_rules"]:
        lines.append("")
        lines.append("# ── Promoted routing rules ──")
        for rule in additions["routing_rules"]:
            lines.append(f'  - pattern: "{rule["pattern"]}"')
            lines.append(f'    target: {rule["target"]}')
    return "\n".join(lines) + "\n"


def apply_to_agency_yaml(path: str, additions: dict[str, Any]) -> int:
    """Append promoted stubs before the routing-rules block and rules at EOF.

    Returns the number of ecosystem entries written. Idempotent per key only at
    the call site (callers should pass already-filtered additions).
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    new_eco_lines: list[str] = []
    for key, entry in additions["ecosystem"].items():
        new_eco_lines.append(f"\n  {key}:")
        new_eco_lines.append(f'    repo: {entry["repo"]}')
        new_eco_lines.append(f'    owner: {entry["owner"]}')
        new_eco_lines.append(f'    url: {entry["url"]}')
        new_eco_lines.append(f'    role: "{entry["role"]}"')
        new_eco_lines.append(f'    bus_channel: "{entry["bus_channel"]}"')
        new_eco_lines.append(f'    protocol: {entry["protocol"]}')
        new_eco_lines.append("    priority: 2")
        tags = ", ".join(entry["tags"])
        new_eco_lines.append(f"    tags: [{tags}]")

    new_rule_lines: list[str] = []
    for rule in additions["routing_rules"]:
        new_rule_lines.append(f'  - pattern: "{rule["pattern"]}"')
        new_rule_lines.append(f'    target: {rule["target"]}')

    # Locate the routing_rules block by its ASCII key (robust to unicode
    # decorative dashes elsewhere in the file).
    m = re.search(r"^routing_rules:\s*$", text, re.MULTILINE)
    if m and new_eco_lines:
        insert_at = m.start()
        text = text[:insert_at] + "\n".join(new_eco_lines) + "\n" + text[insert_at:]

    if new_rule_lines:
        if not text.endswith("\n"):
            text += "\n"
        text += "\n".join(new_rule_lines) + "\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return len(additions["ecosystem"])


def load_existing(config_path: str) -> tuple[set[str], set[str]]:
    """Return (ecosystem keys, routing targets) already present in config."""
    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    keys = set((data.get("ecosystem") or {}).keys())
    targets = {r.get("target") for r in (data.get("routing_rules") or []) if isinstance(r, dict)}
    return keys, targets
