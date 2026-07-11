"""Human-in-the-loop approval manager."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sahiixx_agency.core.models import AgencyTask, ApprovalRequest, RiskLevel


class ApprovalManager:
    """Track pending and approved risky tasks."""

    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}
        self._by_task: dict[str, str] = {}

    def request_approval(self, task: AgencyTask, risk_level: RiskLevel, reason: str) -> ApprovalRequest:
        request_id = f"apr_{uuid.uuid4().hex[:8]}"
        req = ApprovalRequest(
            id=request_id,
            task_id=task.id,
            risk_level=risk_level,
            reason=reason,
        )
        self._requests[request_id] = req
        self._by_task[task.id] = request_id
        return req

    def approve(self, request_id: str, by: str) -> ApprovalRequest | None:
        req = self._requests.get(request_id)
        if req is None:
            return None
        req.status = "approved"
        req.approved_by = by
        req.approved_at = datetime.now(timezone.utc)
        return req

    def reject(self, request_id: str, by: str) -> ApprovalRequest | None:
        req = self._requests.get(request_id)
        if req is None:
            return None
        req.status = "rejected"
        req.approved_by = by
        req.approved_at = datetime.now(timezone.utc)
        return req

    def approve_by_task(self, task_id: str, by: str) -> ApprovalRequest | None:
        request_id = self._by_task.get(task_id)
        if request_id is None:
            return None
        return self.approve(request_id, by)

    def reject_by_task(self, task_id: str, by: str) -> ApprovalRequest | None:
        """Reject the pending approval (if any) associated with ``task_id``."""
        request_id = self._by_task.get(task_id)
        if request_id is None:
            return None
        return self.reject(request_id, by)

    def is_approved(self, task_id: str) -> bool:
        request_id = self._by_task.get(task_id)
        if not request_id:
            return False
        return self._requests[request_id].status == "approved"

    def is_rejected(self, task_id: str) -> bool:
        request_id = self._by_task.get(task_id)
        if not request_id:
            return False
        return self._requests[request_id].status == "rejected"

    def list_pending(self) -> list[ApprovalRequest]:
        return [r for r in self._requests.values() if r.status == "pending"]
