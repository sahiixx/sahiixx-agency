"""GCC Outbound skill API endpoints.

Provides GET /skills to list available GCC Outbound skills and
POST /skills/{skill_id}/run to execute one through the adapter.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sahiixx_agency.adapters.skills.gcc_outbound import GccOutboundSkillAdapter

router = APIRouter(prefix="/skills", tags=["skills"])

SKILL_DIR = Path(__file__).parent.parent.parent / "skills" / "gcc_outbound"


def _parse_manifest(path: Path) -> dict[str, Any]:
    """Parse a manifest.md file, splitting YAML frontmatter and body text."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {"meta": {}, "body": text, "input_schema": None}

    end = text.find("---", 3)
    if end == -1:
        return {"meta": {}, "body": text, "input_schema": None}

    frontmatter = text[3:end].strip()
    body = text[end + 3 :].strip()
    meta = yaml.safe_load(frontmatter) or {}

    input_schema = None
    if "## Input Schema" in body:
        block_start = body.find("## Input Schema")
        block = body[block_start:]
        code_start = block.find("```json")
        if code_start != -1:
            code_start += len("```json")
            code_end = block.find("```", code_start)
            if code_end != -1:
                try:
                    input_schema = json.loads(block[code_start:code_end].strip())
                except json.JSONDecodeError:
                    input_schema = None

    return {"meta": meta, "body": body, "input_schema": input_schema}


def _collect_required_fields(schema: dict[str, Any] | None) -> list[str]:
    """Return top-level required keys from a JSON schema fragment."""
    if schema is None:
        return []
    required = schema.get("required")
    if isinstance(required, list):
        return [str(k) for k in required]
    return []


def _list_gcc_skills() -> list[dict[str, Any]]:
    """Discover all GCC Outbound skill manifests under skills/gcc_outbound."""
    if not SKILL_DIR.exists():
        return []

    skills: list[dict[str, Any]] = []
    for skill_dir in sorted(SKILL_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        manifest_path = skill_dir / "manifest.md"
        if not manifest_path.exists():
            continue

        parsed = _parse_manifest(manifest_path)
        meta = parsed["meta"]
        name = str(meta.get("name", skill_dir.name))
        skill_id = meta.get("id", name) if meta.get("id") else name
        skill_id = str(skill_id)
        description = ""
        if "## Goal" in parsed["body"]:
            goal_start = parsed["body"].find("## Goal") + len("## Goal")
            goal_end = parsed["body"].find("##", goal_start)
            if goal_end == -1:
                goal_end = len(parsed["body"])
            description = parsed["body"][goal_start:goal_end].strip()

        skills.append({
            "id": skill_id,
            "name": name,
            "description": description,
            "tags": meta.get("tags", []),
            "version": meta.get("version", "0.0.0"),
            "input_schema": parsed["input_schema"],
        })

    return skills


@router.get("")
async def list_skills() -> dict[str, Any]:
    """List all GCC Outbound skill metadata."""
    return {"skills": _list_gcc_skills()}


class RunSkillRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    async_: bool = Field(default=False, alias="async")


@router.post("/{skill_id}/run")
async def run_skill(skill_id: str, request: RunSkillRequest) -> dict[str, Any]:
    """Run a GCC Outbound skill by id with the supplied JSON payload."""
    skills = {s["id"]: s for s in _list_gcc_skills()}
    skill_meta = skills.get(skill_id)
    if skill_meta is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    required = _collect_required_fields(skill_meta.get("input_schema"))
    missing = [key for key in required if key not in request.payload]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")

    adapter = GccOutboundSkillAdapter()
    try:
        # Manifest uses hyphen IDs; adapter expects underscore skill names.
        adapter_skill = skill_id.replace("-", "_")
        result = await adapter.execute({"skill": adapter_skill, "context": request.payload})
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    task_id = None
    if request.async_:
        task_id = f"task_{uuid.uuid4().hex[:12]}"

    return {"status": "success", "result": result, "task_id": task_id}
