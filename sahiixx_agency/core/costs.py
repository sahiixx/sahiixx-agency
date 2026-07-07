"""Per-tenant/per-project cost tracking for the agency."""

from __future__ import annotations

from typing import Any

from .memory import AgencyMemory
from .models import CostRecord


class CostLedger:
    """Records, retrieves, and aggregates agency cost records in memory."""

    COST_EVENT_TOPIC: str = "cost.record"

    def __init__(self, memory: AgencyMemory) -> None:
        self.memory = memory

    def record(self, record: CostRecord) -> CostRecord:
        """Persist a cost record to memory."""
        self.memory.log_event(self.COST_EVENT_TOPIC, record.model_dump(mode="json"))
        return record

    def list_records(
        self,
        tenant_id: str | None = None,
        project_id: str | None = None,
        category: str | None = None,
        limit: int = 1_000,
    ) -> list[CostRecord]:
        """Return cost records, optionally filtered by tenant, project, and category."""
        # Load all cost.record events; cost records are append-only and expected to be
        # small. Filter in memory, then enforce ``limit`` on the matching result set.
        # TODO: Add backend filtering if event volume grows.
        events = self.memory.recent_events(topic=self.COST_EVENT_TOPIC, limit=1_000_000)
        records: list[CostRecord] = []
        for event in events:
            payload = event.get("payload") or {}
            try:
                record = CostRecord.model_validate(payload)
            except Exception:
                continue
            if tenant_id is not None and record.tenant_id != tenant_id:
                continue
            if project_id is not None and record.project_id != project_id:
                continue
            if category is not None and record.category != category:
                continue
            records.append(record)
        return records[:limit]

    def summary(
        self,
        tenant_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Return aggregate costs: total and by category."""
        records = self.list_records(
            tenant_id=tenant_id,
            project_id=project_id,
            limit=10_000,
        )
        total = sum(r.amount for r in records)
        by_category: dict[str, float] = {}
        for r in records:
            by_category[r.category] = by_category.get(r.category, 0.0) + r.amount

        return {
            "total": round(total, 6),
            "by_category": {k: round(v, 6) for k, v in by_category.items()},
            "currency": "USD",
            "record_count": len(records),
        }
