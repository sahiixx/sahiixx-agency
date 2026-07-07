"""Base adapter using the generic repo runner."""

from __future__ import annotations

from typing import Any

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.runner import CloneManager, RepoRunner
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy


class BaseAdapter:
    """Base adapter that clones and runs repos."""

    def __init__(
        self,
        clone_base_dir: str = "./data/repos",
        network_policy: NetworkPolicy | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.runner = RepoRunner(
            CloneManager(clone_base_dir),
            network_policy=network_policy,
            audit_logger=audit_logger,
        )

    async def run(self, module: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.runner.run(
            module,
            command=payload.get("command", "run"),
            env=payload.get("env"),
            timeout=payload.get("timeout", 60),
        )
