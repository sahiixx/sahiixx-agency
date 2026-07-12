"""LinkedIn API adapter for OPA.

Provides LinkedIn integration for posting content, fetching analytics,
and managing company pages via the LinkedIn Marketing API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy

LINKEDIN_API_BASE = "https://api.linkedin.com/v2"


@dataclass
class LinkedInResult:
    """Result of a LinkedIn API operation."""

    ok: bool
    operation: str
    status_code: int
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.metadata.get("status"):
            self.metadata["status"] = "success" if self.ok else "failed"


class LinkedInAdapter:
    """Adapter for LinkedIn API operations."""

    def __init__(
        self,
        access_token: str | None = None,
        org_id: str | None = None,
        network_policy: NetworkPolicy | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.access_token = access_token or os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
        self.org_id = org_id or os.environ.get("LINKEDIN_ORG_ID", "")
        self.network_policy = network_policy
        self.audit_logger = audit_logger

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def post(
        self,
        author: str,
        text: str,
        media_url: str | None = None,
        visibility: str = "PUBLIC",
    ) -> LinkedInResult:
        """Post content to LinkedIn.

        Args:
            author: LinkedIn author URN (e.g., "urn:li:person:xxxxx" or "urn:li:organization:xxxxx")
            text: Post text content
            media_url: Optional media URL to attach
            visibility: Post visibility (PUBLIC, CONNECTIONS, etc.)

        Returns:
            LinkedInResult with post data or error.
        """
        payload: dict[str, Any] = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.NetworkVisibility": visibility},
        }

        if media_url:
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                {"status": "READY", "originalUrl": media_url}
            ]
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] = "ARTICLE"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{LINKEDIN_API_BASE}/ugcPosts",
                    headers=self._headers(),
                    json=payload,
                )
                data = resp.json() if resp.status_code < 400 else {"error": resp.text}
                return LinkedInResult(
                    ok=resp.status_code < 400,
                    operation="post",
                    status_code=resp.status_code,
                    data=data,
                    error=data.get("error", ""),
                    metadata={"author": author, "text_length": len(text)},
                )
        except Exception as e:
            return LinkedInResult(ok=False, operation="post", status_code=0, error=str(e))

    async def get_profile(self, person_id: str = "me") -> LinkedInResult:
        """Get LinkedIn profile information."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{LINKEDIN_API_BASE}/people/{person_id}",
                    headers=self._headers(),
                )
                data = resp.json() if resp.status_code < 400 else {"error": resp.text}
                return LinkedInResult(
                    ok=resp.status_code < 400,
                    operation="get_profile",
                    status_code=resp.status_code,
                    data=data,
                    error=data.get("error", ""),
                )
        except Exception as e:
            return LinkedInResult(ok=False, operation="get_profile", status_code=0, error=str(e))

    async def get_organization(self, org_id: str | None = None) -> LinkedInResult:
        """Get LinkedIn organization/company page info."""
        org = org_id or self.org_id
        if not org:
            return LinkedInResult(ok=False, operation="get_organization", status_code=400, error="No org_id provided")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{LINKEDIN_API_BASE}/organizations/{org}",
                    headers=self._headers(),
                )
                data = resp.json() if resp.status_code < 400 else {"error": resp.text}
                return LinkedInResult(
                    ok=resp.status_code < 400,
                    operation="get_organization",
                    status_code=resp.status_code,
                    data=data,
                    error=data.get("error", ""),
                )
        except Exception as e:
            return LinkedInResult(ok=False, operation="get_organization", status_code=0, error=str(e))

    async def get_analytics(self, org_id: str | None = None, days: int = 30) -> LinkedInResult:
        """Get LinkedIn analytics for organization."""
        org = org_id or self.org_id
        if not org:
            return LinkedInResult(ok=False, operation="get_analytics", status_code=400, error="No org_id provided")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{LINKEDIN_API_BASE}/organizationalEntityFollowerStatistics",
                    headers=self._headers(),
                    params={"q": "organizationalEntity", "organization": org},
                )
                data = resp.json() if resp.status_code < 400 else {"error": resp.text}
                return LinkedInResult(
                    ok=resp.status_code < 400,
                    operation="get_analytics",
                    status_code=resp.status_code,
                    data=data,
                    error=data.get("error", ""),
                    metadata={"org_id": org, "days": days},
                )
        except Exception as e:
            return LinkedInResult(ok=False, operation="get_analytics", status_code=0, error=str(e))

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        """Conform to the agency adapter interface."""
        operation = payload.get("operation", "post")

        if operation == "post":
            result = await self.post(
                author=payload.get("author", ""),
                text=payload.get("text", ""),
                media_url=payload.get("media_url"),
                visibility=payload.get("visibility", "PUBLIC"),
            )
        elif operation == "get_profile":
            result = await self.get_profile(payload.get("person_id", "me"))
        elif operation == "get_organization":
            result = await self.get_organization(payload.get("org_id"))
        elif operation == "get_analytics":
            result = await self.get_analytics(payload.get("org_id"), payload.get("days", 30))
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
