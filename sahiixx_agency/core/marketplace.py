"""Marketplace for discovering, installing, and rating agency modules."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from .dependency_scanner import DependencyScanner
from .memory import AgencyMemory
from .models import MarketplaceListing, MarketplaceRating, RepoCategory, RepoNode
from .registry import RepoRegistry
from .runner import CloneManager, CloneManagerLike
from .security import AuditLogger, NetworkPolicy

logger = logging.getLogger(__name__)


class MarketplaceManager:
    """Overlay marketplace metadata on top of RepoRegistry."""

    def __init__(
        self,
        registry: RepoRegistry,
        memory: AgencyMemory,
        clone_manager: CloneManagerLike | None = None,
        data_dir: str = "./data",
        network_policy: NetworkPolicy | None = None,
        audit_logger: AuditLogger | None = None,
        dependency_scanner: DependencyScanner | None = None,
    ) -> None:
        self.registry = registry
        self.memory = memory
        self.clone_manager = clone_manager or CloneManager(f"{data_dir}/repos")
        self.network_policy = network_policy
        self.audit_logger = audit_logger
        self.dependency_scanner = dependency_scanner

    def _install_key(self, module_id: str) -> str:
        return f"marketplace:installs:{module_id}"

    def _ratings_key(self, module_id: str) -> str:
        return f"marketplace:ratings:{module_id}"

    def _enabled_key(self, project_id: str) -> str:
        return f"marketplace:enabled:{project_id}"

    def _get_install_count(self, module_id: str) -> int:
        raw = self.memory.get(self._install_key(module_id), default={"count": 0})
        if isinstance(raw, dict):
            return int(raw.get("count", 0))
        return 0

    def _set_install_count(self, module_id: str, count: int) -> None:
        self.memory.set(self._install_key(module_id), {"count": count})

    def _get_ratings(self, module_id: str) -> list[MarketplaceRating]:
        raw = self.memory.get(self._ratings_key(module_id), default=[])
        if not isinstance(raw, list):
            return []
        return [MarketplaceRating.model_validate(r) for r in raw]

    def _set_ratings(self, module_id: str, ratings: list[MarketplaceRating]) -> None:
        self.memory.set(
            self._ratings_key(module_id),
            [r.model_dump(mode="json") for r in ratings],
        )

    def _is_enabled_for_project(self, module_id: str, project_id: str) -> bool:
        enabled = self.memory.get(self._enabled_key(project_id), default=[])
        if not isinstance(enabled, list):
            return False
        return module_id in enabled

    def is_enabled_for_project(self, module_id: str, project_id: str) -> bool:
        """Public accessor for project enablement checks."""
        return self._is_enabled_for_project(module_id, project_id)

    def _check_network_policy(self, node: RepoNode) -> None:
        """Verify declared external hosts against the egress policy.

        Raises RuntimeError and logs an audit event when a host is blocked.
        Mirrors RepoRunner._check_network_policy for consistent enforcement.
        """
        policy = self.network_policy
        if policy is None or policy.allow_all:
            return

        hosts = node.external_hosts or []
        if not hosts:
            return

        blocked = [host for host in hosts if not policy.is_allowed(host)]
        if blocked:
            message = (
                f"Network policy blocks outbound hosts for module {node.full_name}: "
                f"{', '.join(blocked)}"
            )
            if self.audit_logger is not None:
                self.audit_logger.log(
                    "network_policy_violation",
                    "MarketplaceManager",
                    node.id,
                    {"blocked_hosts": blocked, "allowlist": sorted(policy.allowlist)},
                )
            else:
                logger.warning("network_policy_violation: %s", message)
            raise RuntimeError(message)

    def _build_listing(
        self,
        module: RepoNode,
        project_id: str | None = None,
    ) -> MarketplaceListing:
        ratings = self._get_ratings(module.id)
        count = len(ratings)
        average = sum(r.score for r in ratings) / count if count else 0.0
        enabled_projects: list[str] = []
        if project_id and self._is_enabled_for_project(module.id, project_id):
            enabled_projects.append(project_id)
        install_count = self._get_install_count(module.id)
        return MarketplaceListing(
            module=module,
            install_count=install_count,
            average_rating=average,
            rating_count=count,
            installed_globally=install_count > 0,
            enabled_projects=enabled_projects,
        )

    async def list_modules(
        self,
        project_id: str | None = None,
        query: str = "",
        category: RepoCategory | None = None,
    ) -> list[MarketplaceListing]:
        """Return marketplace listings, optionally filtered."""
        listings: list[MarketplaceListing] = []
        for module in self.registry.modules:
            if query and query.lower() not in module.name.lower() and query.lower() not in (module.description or "").lower():
                continue
            if category and module.category != category:
                continue
            listings.append(self._build_listing(module, project_id=project_id))
        listings.sort(
            key=lambda x: (x.average_rating, x.install_count, x.module.stars),
            reverse=True,
        )
        return listings

    async def get_module(
        self,
        module_id: str,
        project_id: str | None = None,
    ) -> MarketplaceListing | None:
        module = self.registry.get(module_id)
        if module is None:
            return None
        return self._build_listing(module, project_id=project_id)

    async def install_module(self, module_id: str) -> MarketplaceListing:
        module = self.registry.get(module_id)
        if module is None:
            raise ValueError(f"Module {module_id} not found")
        self._check_network_policy(module)
        await self.clone_manager.clone(module)
        if self.dependency_scanner is not None:
            report = await self.dependency_scanner.scan(module)
            if not report.passed:
                if self.audit_logger is not None:
                    self.audit_logger.log(
                        "dependency_scan_failed",
                        "MarketplaceManager",
                        module_id,
                        {"failures": report.failures, "command": report.command},
                    )
                raise RuntimeError(f"Dependency scan failed for {module_id}")
        count = self._get_install_count(module_id) + 1
        self._set_install_count(module_id, count)
        if self.audit_logger is not None:
            self.audit_logger.log(
                "module_installed",
                "MarketplaceManager",
                module_id,
                {"install_count": count},
            )
        return await self.get_module(module_id)

    async def enable_module(self, module_id: str, project_id: str) -> MarketplaceListing:
        module = self.registry.get(module_id)
        if module is None:
            raise ValueError(f"Module {module_id} not found")
        if self._get_install_count(module_id) == 0:
            await self.install_module(module_id)
        enabled = set(self.memory.get(self._enabled_key(project_id), default=[]))
        enabled.add(module_id)
        self.memory.set(self._enabled_key(project_id), sorted(enabled))
        if self.audit_logger is not None:
            self.audit_logger.log(
                "module_enabled",
                "MarketplaceManager",
                module_id,
                {"project_id": project_id},
            )
        return await self.get_module(module_id, project_id=project_id)

    async def disable_module(self, module_id: str, project_id: str) -> MarketplaceListing:
        module = self.registry.get(module_id)
        if module is None:
            raise ValueError(f"Module {module_id} not found")
        enabled = set(self.memory.get(self._enabled_key(project_id), default=[]))
        enabled.discard(module_id)
        self.memory.set(self._enabled_key(project_id), sorted(enabled))
        if self.audit_logger is not None:
            self.audit_logger.log(
                "module_disabled",
                "MarketplaceManager",
                module_id,
                {"project_id": project_id},
            )
        return await self.get_module(module_id, project_id=project_id)

    async def rate_module(
        self,
        module_id: str,
        user_id: str,
        score: float,
        review: str = "",
    ) -> MarketplaceListing:
        module = self.registry.get(module_id)
        if module is None:
            raise ValueError(f"Module {module_id} not found")
        ratings = [r for r in self._get_ratings(module_id) if r.user_id != user_id]
        ratings.append(
            MarketplaceRating(
                id=f"rating_{uuid.uuid4().hex[:12]}",
                module_id=module_id,
                user_id=user_id,
                score=score,
                review=review,
                timestamp=datetime.now(timezone.utc),
            )
        )
        self._set_ratings(module_id, ratings)
        if self.audit_logger is not None:
            self.audit_logger.log(
                "module_rated",
                "MarketplaceManager",
                module_id,
                {"user_id": user_id, "score": score, "review": review},
            )
        return await self.get_module(module_id)
