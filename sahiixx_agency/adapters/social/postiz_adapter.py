"""Postiz API adapter for OPA.

Dispatches social media posts, schedules, and analytics queries to a
self-hosted or cloud Postiz instance via its Public API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy

POSTIZ_API_BASE = "http://localhost:3000/public/v1"


@dataclass
class PostizResult:
    """Result of a Postiz API operation."""

    ok: bool
    operation: str
    status_code: int
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.metadata.get("status"):
            self.metadata["status"] = "success" if self.ok else "failed"


class PostizAdapter:
    """Adapter for Postiz API operations."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        network_policy: NetworkPolicy | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("POSTIZ_API_KEY", "")
        self.base_url = base_url or os.environ.get("POSTIZ_API_URL", POSTIZ_API_BASE)
        self.network_policy = network_policy
        self.audit_logger = audit_logger

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> PostizResult:
        """Make an authenticated request to the Postiz API."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.request(
                    method,
                    f"{self.base_url}{path}",
                    headers=self._headers(),
                    json=json_data,
                    params=params,
                )
                data = resp.json() if resp.status_code < 400 else {"error": resp.text}
                return PostizResult(
                    ok=resp.status_code < 400,
                    operation=f"{method} {path}",
                    status_code=resp.status_code,
                    data=data,
                    error=data.get("error", ""),
                )
        except Exception as e:
            return PostizResult(ok=False, operation=f"{method} {path}", status_code=0, error=str(e))

    # ─── Integrations ──────────────────────────────────────────

    async def list_integrations(self) -> PostizResult:
        """List all connected social media channels."""
        return await self._request("GET", "/integrations")

    async def get_integration(self, integration_id: str) -> PostizResult:
        """Get details for a specific integration."""
        return await self._request("GET", f"/integrations/{integration_id}")

    async def delete_integration(self, integration_id: str) -> PostizResult:
        """Delete a connected channel."""
        return await self._request("DELETE", f"/integrations/{integration_id}")

    # ─── Posts ─────────────────────────────────────────────────

    async def create_post(
        self,
        integration_id: str,
        content: str,
        images: list[dict[str, str]] | None = None,
        platform_type: str = "x",
        schedule_date: str | None = None,
        settings: dict[str, Any] | None = None,
    ) -> PostizResult:
        """Create and optionally schedule a post.

        Args:
            integration_id: The integration/channel ID from Postiz
            content: Post text content
            images: List of image objects with 'id' and 'path' keys
            platform_type: Platform type (x, linkedin, instagram, etc.)
            schedule_date: ISO date string for scheduling (None = post now)
            settings: Platform-specific settings override

        Returns:
            PostizResult with post data.
        """
        post_type = "now" if not schedule_date else "schedule"
        image_list = images or []

        payload = {
            "type": post_type,
            "date": schedule_date or "",
            "shortLink": False,
            "tags": [],
            "posts": [
                {
                    "integration": {"id": integration_id},
                    "value": [
                        {
                            "content": content,
                            "image": image_list,
                        }
                    ],
                    "settings": settings or {"__type": platform_type},
                }
            ],
        }

        return await self._request("POST", "/posts", json_data=payload)

    async def list_posts(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> PostizResult:
        """List posts within a date range."""
        params = {}
        if start_date:
            params["start"] = start_date
        if end_date:
            params["end"] = end_date
        return await self._request("GET", "/posts", params=params)

    async def delete_post(self, post_id: str) -> PostizResult:
        """Delete a post by ID."""
        return await self._request("DELETE", f"/posts/{post_id}")

    async def change_post_status(self, post_id: str, status: str) -> PostizResult:
        """Change post status (draft/schedule)."""
        return await self._request("PATCH", f"/posts/{post_id}/status", json_data={"status": status})

    # ─── Upload ────────────────────────────────────────────────

    async def upload_file(self, file_path: str) -> PostizResult:
        """Upload a media file."""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                with open(file_path, "rb") as f:
                    resp = await client.post(
                        f"{self.base_url}/upload",
                        headers={"Authorization": self.api_key},
                        files={"file": (os.path.basename(file_path), f)},
                    )
                data = resp.json() if resp.status_code < 400 else {"error": resp.text}
                return PostizResult(
                    ok=resp.status_code < 400,
                    operation="upload_file",
                    status_code=resp.status_code,
                    data=data,
                    error=data.get("error", ""),
                )
        except Exception as e:
            return PostizResult(ok=False, operation="upload_file", status_code=0, error=str(e))

    async def upload_from_url(self, url: str) -> PostizResult:
        """Upload a file from a URL."""
        return await self._request("POST", "/upload-from-url", json_data={"url": url})

    # ─── Analytics ─────────────────────────────────────────────

    async def get_channel_analytics(self, integration_id: str) -> PostizResult:
        """Get analytics for a specific channel."""
        return await self._request("GET", f"/integrations/{integration_id}/analytics")

    async def get_post_analytics(self, post_id: str) -> PostizResult:
        """Get analytics for a specific post."""
        return await self._request("GET", f"/posts/{post_id}/analytics")

    # ─── Notifications ─────────────────────────────────────────

    async def list_notifications(self, page: int = 0) -> PostizResult:
        """List notifications."""
        return await self._request("GET", "/notifications", params={"page": page})

    # ─── Dispatch (OPA adapter interface) ──────────────────────

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        """Conform to the agency adapter interface."""
        operation = payload.get("operation", "create_post")

        if operation == "create_post":
            result = await self.create_post(
                integration_id=payload.get("integration_id", ""),
                content=payload.get("content", ""),
                images=payload.get("images"),
                platform_type=payload.get("platform_type", "x"),
                schedule_date=payload.get("schedule_date"),
                settings=payload.get("settings"),
            )
        elif operation == "list_integrations":
            result = await self.list_integrations()
        elif operation == "list_posts":
            result = await self.list_posts(
                start_date=payload.get("start_date"),
                end_date=payload.get("end_date"),
            )
        elif operation == "delete_post":
            result = await self.delete_post(payload.get("post_id", ""))
        elif operation == "upload_file":
            result = await self.upload_file(payload.get("file_path", ""))
        elif operation == "get_channel_analytics":
            result = await self.get_channel_analytics(payload.get("integration_id", ""))
        elif operation == "get_post_analytics":
            result = await self.get_post_analytics(payload.get("post_id", ""))
        elif operation == "list_notifications":
            result = await self.list_notifications(payload.get("page", 0))
        else:
            return {"module": node.name, "status": "failed", "error": f"Unknown operation: {operation}"}

        return {
            "module": node.name,
            "operation": result.operation,
            "status": result.metadata.get("status", "failed"),
            "status_code": result.status_code,
            "data": result.data,
            "error": result.error,
        }
