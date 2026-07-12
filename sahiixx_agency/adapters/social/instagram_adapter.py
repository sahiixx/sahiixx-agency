"""Instagram API adapter for OPA.

Provides Instagram integration for posting content, fetching analytics,
and managing media via the Instagram Graph API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from sahiixx_agency.core.models import RepoNode
from sahiixx_agency.core.security import AuditLogger, NetworkPolicy

INSTAGRAM_API_BASE = "https://graph.facebook.com/v18.0"


@dataclass
class InstagramResult:
    """Result of an Instagram API operation."""

    ok: bool
    operation: str
    status_code: int
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.metadata.get("status"):
            self.metadata["status"] = "success" if self.ok else "failed"


class InstagramAdapter:
    """Adapter for Instagram Graph API operations."""

    def __init__(
        self,
        access_token: str | None = None,
        ig_user_id: str | None = None,
        network_policy: NetworkPolicy | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.access_token = access_token or os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
        self.ig_user_id = ig_user_id or os.environ.get("INSTAGRAM_USER_ID", "")
        self.network_policy = network_policy
        self.audit_logger = audit_logger

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    async def post_image(
        self,
        image_url: str,
        caption: str,
        user_id: str | None = None,
    ) -> InstagramResult:
        """Post an image to Instagram.

        Args:
            image_url: Public URL of the image to post
            caption: Post caption
            user_id: Instagram Business Account ID (uses configured ID if not provided)

        Returns:
            InstagramResult with container ID or error.
        """
        ig_user = user_id or self.ig_user_id
        if not ig_user:
            return InstagramResult(ok=False, operation="post_image", status_code=400, error="No IG user ID configured")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Step 1: Create media container
                resp = await client.post(
                    f"{INSTAGRAM_API_BASE}/{ig_user}/media",
                    headers=self._headers(),
                    params={"access_token": self.access_token},
                    json={
                        "image_url": image_url,
                        "caption": caption,
                    },
                )
                container_data = resp.json() if resp.status_code < 400 else {"error": resp.text}

                if resp.status_code >= 400:
                    return InstagramResult(ok=False, operation="post_image", status_code=resp.status_code, data=container_data, error=container_data.get("error", {}).get("message", str(container_data)))

                container_id = container_data.get("id")
                if not container_id:
                    return InstagramResult(ok=False, operation="post_image", status_code=200, error="No container ID returned")

                # Step 2: Publish the container
                pub_resp = await client.post(
                    f"{INSTAGRAM_API_BASE}/{ig_user}/media_publish",
                    headers=self._headers(),
                    params={"access_token": self.access_token},
                    json={"creation_id": container_id},
                )
                pub_data = pub_resp.json() if pub_resp.status_code < 400 else {"error": pub_resp.text}

                return InstagramResult(
                    ok=pub_resp.status_code < 400,
                    operation="post_image",
                    status_code=pub_resp.status_code,
                    data=pub_data,
                    error=pub_data.get("error", {}).get("message", ""),
                    metadata={"container_id": container_id, "media_id": pub_data.get("id")},
                )
        except Exception as e:
            return InstagramResult(ok=False, operation="post_image", status_code=0, error=str(e))

    async def post_carousel(
        self,
        media_urls: list[str],
        caption: str,
        user_id: str | None = None,
    ) -> InstagramResult:
        """Post a carousel to Instagram."""
        ig_user = user_id or self.ig_user_id
        if not ig_user:
            return InstagramResult(ok=False, operation="post_carousel", status_code=400, error="No IG user ID configured")

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # Create containers for each image
                children = []
                for url in media_urls:
                    resp = await client.post(
                        f"{INSTAGRAM_API_BASE}/{ig_user}/media",
                        headers=self._headers(),
                        params={"access_token": self.access_token},
                        json={"image_url": url, "is_carousel_item": True},
                    )
                    if resp.status_code >= 400:
                        return InstagramResult(ok=False, operation="post_carousel", status_code=resp.status_code, error=str(resp.json()))
                    children.append(resp.json().get("id"))

                # Create carousel container
                resp = await client.post(
                    f"{INSTAGRAM_API_BASE}/{ig_user}/media",
                    headers=self._headers(),
                    params={"access_token": self.access_token},
                    json={
                        "media_type": "CAROUSEL",
                        "children": ",".join(children),
                        "caption": caption,
                    },
                )
                container_data = resp.json() if resp.status_code < 400 else {"error": resp.text}
                container_id = container_data.get("id")

                if not container_id:
                    return InstagramResult(ok=False, operation="post_carousel", status_code=200, error="No container ID")

                # Publish
                pub_resp = await client.post(
                    f"{INSTAGRAM_API_BASE}/{ig_user}/media_publish",
                    headers=self._headers(),
                    params={"access_token": self.access_token},
                    json={"creation_id": container_id},
                )
                pub_data = pub_resp.json() if pub_resp.status_code < 400 else {"error": pub_resp.text}

                return InstagramResult(
                    ok=pub_resp.status_code < 400,
                    operation="post_carousel",
                    status_code=pub_resp.status_code,
                    data=pub_data,
                    error=pub_data.get("error", {}).get("message", ""),
                    metadata={"media_count": len(children)},
                )
        except Exception as e:
            return InstagramResult(ok=False, operation="post_carousel", status_code=0, error=str(e))

    async def post_reel(
        self,
        video_url: str,
        caption: str,
        user_id: str | None = None,
    ) -> InstagramResult:
        """Post a Reel to Instagram."""
        ig_user = user_id or self.ig_user_id
        if not ig_user:
            return InstagramResult(ok=False, operation="post_reel", status_code=400, error="No IG user ID configured")

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # Create video container
                resp = await client.post(
                    f"{INSTAGRAM_API_BASE}/{ig_user}/media",
                    headers=self._headers(),
                    params={"access_token": self.access_token},
                    json={
                        "media_type": "REELS",
                        "video_url": video_url,
                        "caption": caption,
                    },
                )
                container_data = resp.json() if resp.status_code < 400 else {"error": resp.text}
                container_id = container_data.get("id")

                if not container_id:
                    return InstagramResult(ok=False, operation="post_reel", status_code=200, error="No container ID")

                # Wait for processing and publish
                import asyncio
                await asyncio.sleep(5)

                pub_resp = await client.post(
                    f"{INSTAGRAM_API_BASE}/{ig_user}/media_publish",
                    headers=self._headers(),
                    params={"access_token": self.access_token},
                    json={"creation_id": container_id},
                )
                pub_data = pub_resp.json() if pub_resp.status_code < 400 else {"error": pub_resp.text}

                return InstagramResult(
                    ok=pub_resp.status_code < 400,
                    operation="post_reel",
                    status_code=pub_resp.status_code,
                    data=pub_data,
                    error=pub_data.get("error", {}).get("message", ""),
                )
        except Exception as e:
            return InstagramResult(ok=False, operation="post_reel", status_code=0, error=str(e))

    async def get_media(self, user_id: str | None = None, limit: int = 25) -> InstagramResult:
        """Get recent media from Instagram."""
        ig_user = user_id or self.ig_user_id
        if not ig_user:
            return InstagramResult(ok=False, operation="get_media", status_code=400, error="No IG user ID configured")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{INSTAGRAM_API_BASE}/{ig_user}/media",
                    headers=self._headers(),
                    params={
                        "access_token": self.access_token,
                        "fields": "id,caption,media_type,media_url,timestamp,like_count,comments_count",
                        "limit": limit,
                    },
                )
                data = resp.json() if resp.status_code < 400 else {"error": resp.text}
                return InstagramResult(
                    ok=resp.status_code < 400,
                    operation="get_media",
                    status_code=resp.status_code,
                    data=data,
                    error=data.get("error", {}).get("message", ""),
                )
        except Exception as e:
            return InstagramResult(ok=False, operation="get_media", status_code=0, error=str(e))

    async def get_insights(self, media_id: str) -> InstagramResult:
        """Get insights for a specific media post."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{INSTAGRAM_API_BASE}/{media_id}/insights",
                    headers=self._headers(),
                    params={
                        "access_token": self.access_token,
                        "metric": "impressions,reach,engagement",
                    },
                )
                data = resp.json() if resp.status_code < 400 else {"error": resp.text}
                return InstagramResult(
                    ok=resp.status_code < 400,
                    operation="get_insights",
                    status_code=resp.status_code,
                    data=data,
                    error=data.get("error", {}).get("message", ""),
                )
        except Exception as e:
            return InstagramResult(ok=False, operation="get_insights", status_code=0, error=str(e))

    async def run(self, node: RepoNode, payload: dict[str, Any]) -> dict[str, Any]:
        """Conform to the agency adapter interface."""
        operation = payload.get("operation", "post_image")

        if operation == "post_image":
            result = await self.post_image(
                image_url=payload.get("image_url", ""),
                caption=payload.get("caption", ""),
                user_id=payload.get("user_id"),
            )
        elif operation == "post_carousel":
            result = await self.post_carousel(
                media_urls=payload.get("media_urls", []),
                caption=payload.get("caption", ""),
                user_id=payload.get("user_id"),
            )
        elif operation == "post_reel":
            result = await self.post_reel(
                video_url=payload.get("video_url", ""),
                caption=payload.get("caption", ""),
                user_id=payload.get("user_id"),
            )
        elif operation == "get_media":
            result = await self.get_media(payload.get("user_id"), payload.get("limit", 25))
        elif operation == "get_insights":
            result = await self.get_insights(payload.get("media_id", ""))
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
