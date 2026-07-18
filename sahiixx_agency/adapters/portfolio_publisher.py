"""Publish portfolio entries for newly shipped modules."""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from typing import Any

from sahiixx_agency.adapters.base import BaseAdapter
from sahiixx_agency.adapters.portfolio_entry import (
    ACCENTS,
    ProjectEntry,
    build_prompt,
    entry_from_response,
    next_index,
    render_ts_entry,
    slugify,
)
from sahiixx_agency.core.models import LLMMessage, NotificationChannel

MARKER = "// __OPA_PORTFOLIO_INSERT__"


class PortfolioPublisherAdapter(BaseAdapter):
    """Draft, insert, build, commit, deploy, and notify one portfolio entry."""

    def __init__(
        self,
        *,
        settings: dict[str, Any] | None = None,
        llm_manager: Any | None = None,
        notifications: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.clone_base_dir = kwargs.get("clone_base_dir", "./data/repos")
        self.settings = settings or {}
        self.llm = llm_manager
        self.notifications = notifications

    async def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.settings.get("enabled", False):
            return {"status": "skipped", "reason": "portfolio_publisher disabled"}

        intent = str(payload.get("brief") or payload.get("module") or "")
        module = self._find_module(intent)
        if module is None:
            return await self._fail(f"No registry module matched intent: {intent!r}")
        slug = slugify(str(module.get("name") or module.get("id")))

        skip = self._gates(module, slug)
        if skip:
            return {"status": "skipped", "reason": skip, "module": slug}

        repo = self.settings.get("repo_path", "")
        data_ts = os.path.join(repo, "src", "data.ts")
        original = self._read_file(data_ts)
        if original is None:
            return await self._fail(f"data.ts not readable at {data_ts}")
        if MARKER not in original:
            return await self._fail(f"Insertion marker missing in {data_ts}")
        if not await self._git_clean(repo):
            return await self._fail("portfolio repo has uncommitted changes in src/data.ts")

        existing = self._existing_indices(original)
        index = next_index(existing)
        accent = ACCENTS[len(existing) % len(ACCENTS)]
        year = str(datetime.now(timezone.utc).year)
        readme = self._read_readme(module)
        prompt = build_prompt(module, readme, index=index, accent=accent, year=year)
        try:
            entry = await self._draft(prompt, module=module, index=index, accent=accent, year=year)
        except Exception as exc:  # noqa: BLE001
            return await self._fail(f"LLM drafting failed: {exc}")

        rendered = render_ts_entry(entry)
        if self.settings.get("dry_run", True):
            await self._notify("Portfolio dry-run", f"Rendered entry for {entry.name}:\n\n{rendered}")
            return {"status": "success", "dry_run": True, "module": slug, "entry": rendered}

        self._write_file(data_ts, original.replace(f"  {MARKER}", rendered + "\n  " + MARKER))

        ok, out = await self._run("npm run build", cwd=repo, timeout=300)
        if not ok:
            self._write_file(data_ts, original)
            return await self._fail(f"portfolio build failed, data.ts restored:\n{out[-800:]}")

        ok, out = await self._run("git add src/data.ts", cwd=repo, timeout=60)
        if ok:
            ok, out = await self._run(f'git commit -m "feat: add {slug} to selected work [opa]"', cwd=repo, timeout=60)
        if not ok:
            self._write_file(data_ts, original)
            return await self._fail(f"git commit failed, data.ts restored:\n{out[-800:]}")

        ok, out = await self._run("npx wrangler pages deploy dist", cwd=repo, timeout=600)
        if not ok:
            return await self._fail(f"wrangler deploy failed (entry committed locally):\n{out[-800:]}")

        ok, _ = await self._run("git push", cwd=repo, timeout=120)
        push_note = "" if ok else "\n(git push failed — deploy is live, local commit not pushed)"
        await self._notify(
            "Portfolio updated",
            f"Published {entry.name} ({slug}) to sahiix-portfolio.pages.dev{push_note}",
        )
        return {"status": "success", "module": slug, "index": index, "deployed": True, "pushed": ok}

    # --- lookup + gates ---------------------------------------------------

    def _find_module(self, intent: str) -> dict[str, Any] | None:
        """Best registry match for a free-text intent (longest id/name contained in it)."""
        registry_path = self.settings.get("registry_path", "./data/registry.json")
        try:
            with open(registry_path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return None
        lowered = intent.lower()
        best: dict[str, Any] | None = None
        best_len = 0
        for module in data.get("modules", []):
            if not isinstance(module, dict):
                continue
            for key in (module.get("id"), module.get("name")):
                if key and key.lower() in lowered and len(key) > best_len:
                    best = module
                    best_len = len(key)
        return best

    def _gates(self, module: dict[str, Any], slug: str) -> str | None:
        if module.get("is_fork"):
            return "fork"
        if not (module.get("description") or "").strip():
            return "no description"
        if slug in set(self.settings.get("ignore") or []):
            return "ignored"
        data_ts = os.path.join(self.settings.get("repo_path", ""), "src", "data.ts")
        try:
            with open(data_ts, encoding="utf-8") as fh:
                if f'id: "{slug}"' in fh.read():
                    return "already published"
        except OSError:
            return "data.ts not readable"
        return None

    # --- drafting ---------------------------------------------------------

    async def _draft(
        self,
        prompt: str,
        *,
        module: dict[str, Any],
        index: str,
        accent: str,
        year: str,
    ) -> ProjectEntry:
        if self.llm is None:
            raise RuntimeError("LLM manager not configured")
        response = await self.llm.chat(
            messages=[
                LLMMessage(role="system", content="You output only valid JSON."),
                LLMMessage(role="user", content=prompt),
            ],
            temperature=0.4,
            max_tokens=1500,
        )
        return entry_from_response(response.content, module=module, index=index, accent=accent, year=year)

    def _read_readme(self, module: dict[str, Any]) -> str:
        clone_dir = os.path.join(self.clone_base_dir, str(module.get("name") or ""))
        for candidate in ("README.md", "readme.md", "README.MD"):
            readme = self._read_file(os.path.join(clone_dir, candidate))
            if readme:
                return readme
        return ""

    # --- file + process helpers -------------------------------------------

    @staticmethod
    def _existing_indices(source: str) -> list[str]:
        return re.findall(r'^\s{4}index: "(\d+)"', source, flags=re.MULTILINE)

    @staticmethod
    def _read_file(path: str) -> str | None:
        try:
            with open(path, encoding="utf-8") as fh:
                return fh.read()
        except OSError:
            return None

    @staticmethod
    def _write_file(path: str, content: str) -> None:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)

    async def _git_clean(self, repo: str) -> bool:
        ok, out = await self._run("git status --porcelain -- src/data.ts", cwd=repo, timeout=30)
        return ok and not out.strip()

    async def _run(self, command: str, *, cwd: str, timeout: int) -> tuple[bool, str]:
        def _call() -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                timeout=timeout,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

        try:
            proc = await asyncio.to_thread(_call)
        except (subprocess.TimeoutExpired, OSError) as exc:
            return False, str(exc)
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode == 0, output

    # --- notifications ------------------------------------------------------

    async def _notify(self, title: str, body: str) -> None:
        if self.notifications is None:
            return
        for channel in self.settings.get("notify_channels") or ["sse"]:
            try:
                await self.notifications.send(NotificationChannel(channel), title, body)
            except Exception:  # noqa: BLE001
                continue

    async def _fail(self, reason: str) -> dict[str, Any]:
        await self._notify("Portfolio publish failed", reason)
        return {"status": "failed", "error": reason}
