"""Portfolio entry drafting: prompt building, validation, and TypeScript rendering."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

ACCENTS = ["#f59e0b", "#ff4d4d", "#7c5cff", "#22d3ee", "#34d399", "#f472b6"]


class ProjectEntry(BaseModel):
    """A portfolio `Project` entry (mirrors src/data.ts, minus optional fields)."""

    id: str
    index: str
    name: str
    tagline: str
    description: str
    longDescription: list[str] = Field(min_length=1, max_length=4)
    problem: str
    architecture: str
    statusNote: str
    highlights: list[str] = Field(min_length=2, max_length=6)
    role: str = "Architect & sole engineer"
    status: str = "Shipped"
    stack: list[str] = Field(min_length=1, max_length=10)
    year: str
    url: str
    accent: str


def slugify(name: str) -> str:
    """Kebab-case slug for a module name."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "module"


def next_index(existing: list[str]) -> str:
    """Next zero-padded index after the max existing one (e.g. ["01", "04"] -> "05")."""
    numbers = [int(i) for i in existing if i.isdigit()]
    return f"{max(numbers) + 1 if numbers else 1:02d}"


def build_prompt(module: dict[str, Any], readme: str, *, index: str, accent: str, year: str) -> str:
    """Prompt that makes the LLM return strict JSON for a portfolio entry."""
    meta = {
        "name": module.get("name"),
        "description": module.get("description"),
        "language": module.get("language"),
        "topics": module.get("topics"),
        "stars": module.get("stars"),
        "url": module.get("url"),
    }
    return (
        "You are writing a new entry for Sahil's curated developer portfolio "
        "(sahiix-portfolio.pages.dev). Voice: confident, concrete, engineer-to-engineer; "
        "short sentences; no buzzwords, no emoji, no exclamation marks.\n\n"
        "Module metadata (JSON):\n" + json.dumps(meta, indent=2) + "\n\n"
        "README excerpt:\n" + (readme[:3000] or "(no README available)") + "\n\n"
        "Return ONLY a JSON object with exactly these keys:\n"
        '- "name": display name for THIS module, derived from its name (you may restyle casing/spacing only)\n'
        '- "tagline": one line, <= 80 chars\n'
        '- "description": 2-3 sentences, <= 300 chars\n'
        '- "longDescription": 2 paragraphs, each 1-3 sentences\n'
        '- "problem": the pain it solves, 1-2 sentences\n'
        '- "architecture": key components joined with " · ", one line\n'
        '- "statusNote": where it runs / maturity, one line\n'
        '- "highlights": 3-4 concrete bullets\n'
        '- "role": "Architect & sole engineer"\n'
        '- "status": "Shipped"\n'
        '- "stack": 3-7 technologies\n'
        '- "url": best public URL (live site if obvious, else the repo URL)\n'
        "Do not include id, index, year, or accent — they are set by the caller "
        f"(index {index}, year {year}, accent {accent}). No markdown fences."
    )


def _extract_json(raw: str) -> str:
    """Pull the first {...} block out of an LLM response (handles prose and fences)."""
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("LLM response contained no JSON object")
    return match.group(0)


def entry_from_response(raw: str, *, module: dict[str, Any], index: str, accent: str, year: str) -> ProjectEntry:
    """Parse + validate the LLM JSON response into a ProjectEntry."""
    data = json.loads(_extract_json(raw))
    data["id"] = slugify(str(module.get("name") or module.get("id") or "module"))
    data["index"] = index
    data["accent"] = accent
    data["year"] = year
    data["url"] = module.get("url") or data.get("url") or ""
    if not data.get("name"):
        data["name"] = str(module.get("name") or data["id"])
    return ProjectEntry.model_validate(data)


def _ts_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _ts_string_array(values: list[str], indent: int) -> str:
    pad = " " * indent
    if len(values) <= 5 and all(len(v) < 40 for v in values):
        return "[" + ", ".join(_ts_string(v) for v in values) + "]"
    inner = ",\n".join(f"{pad}  {_ts_string(v)}" for v in values)
    return "[\n" + inner + ",\n" + pad + "]"


def render_ts_entry(entry: ProjectEntry) -> str:
    """Render the entry as a TS object literal matching src/data.ts style (2-space indent)."""
    lines = ["  {"]
    lines.append(f"    id: {_ts_string(entry.id)},")
    lines.append(f"    index: {_ts_string(entry.index)},")
    lines.append(f"    name: {_ts_string(entry.name)},")
    lines.append(f"    tagline: {_ts_string(entry.tagline)},")
    lines.append(f"    description: {_ts_string(entry.description)},")
    lines.append(f"    longDescription: {_ts_string_array(entry.longDescription, 4)},")
    lines.append(f"    problem: {_ts_string(entry.problem)},")
    lines.append(f"    architecture: {_ts_string(entry.architecture)},")
    lines.append(f"    statusNote: {_ts_string(entry.statusNote)},")
    lines.append(f"    highlights: {_ts_string_array(entry.highlights, 4)},")
    lines.append(f"    role: {_ts_string(entry.role)},")
    lines.append(f"    status: {_ts_string(entry.status)},")
    lines.append(f"    stack: {_ts_string_array(entry.stack, 4)},")
    lines.append(f"    year: {_ts_string(entry.year)},")
    lines.append(f"    url: {_ts_string(entry.url)},")
    lines.append(f"    accent: {_ts_string(entry.accent)},")
    lines.append("  },")
    return "\n".join(lines)
