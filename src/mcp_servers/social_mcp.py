"""
Social Media MCP Server - Unified social media posting with approval workflows.

This MCP server provides social media capabilities for the AI Employee system.
All publish operations require prior human approval through the HITL workflow.

Usage:
    from src.mcp_servers import SocialMCP

    server = SocialMCP(vault_path='./AI_Employee_Vault')

    # Draft a post
    result = server.draft_post(
        platform='facebook',
        content='Hello world!',
    )

    # Publish approved post
    result = server.publish_post(draft_id='...', approval_id='...')

Tools provided:
- health: Check platform connection status
- draft_post: Create a post draft for approval
- validate_post: Validate content for a platform
- publish_post: Publish an approved post
- get_engagement: Get metrics for a published post
- platform_status: Get status for a specific platform
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.cloud.work_zone import requires_local
from src.lib.social_clients import (
    BaseSocialClient,
    PostResult,
    FacebookClient,
    InstagramClient,
    TwitterClient,
)
from src.models import Platform, PostStatus, SocialPost
from src.utils.retry_handler import RateLimiter, CircuitBreaker


# Rate limit: 5 posts per day
POSTS_PER_DAY = 5


@dataclass
class SocialResult:
    """Result of a social media operation."""
    success: bool
    action: str
    platform: Optional[str] = None
    draft_id: Optional[str] = None
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "success": self.success,
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.platform:
            result["platform"] = self.platform
        if self.draft_id:
            result["draft_id"] = self.draft_id
        if self.post_id:
            result["post_id"] = self.post_id
        if self.post_url:
            result["post_url"] = self.post_url
        if self.data is not None:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
            result["error_type"] = self.error_type
        return result


class SocialMCP:
    """
    Social Media MCP Server for multi-platform posting.

    Provides unified interface to Facebook, Instagram, and Twitter
    with HITL approval workflow integration.
    """

    def __init__(
        self,
        vault_path: str,
        dry_run: bool = True,
        agent_zone=None,
    ):
        """
        Initialize Social MCP server.

        Args:
            vault_path: Path to the Obsidian vault
            dry_run: If True, don't actually post to platforms
            agent_zone: WorkZone enum value for work-zone enforcement
        """
        self.agent_zone = agent_zone
        self.vault_path = Path(vault_path)
        self.dry_run = dry_run

        # Vault paths
        self.drafts_path = self.vault_path / "Social" / "Drafts"
        self.metrics_path = self.vault_path / "Social" / "Metrics"
        self.logs_path = self.vault_path / "Logs"

        # Ensure directories exist
        self.drafts_path.mkdir(parents=True, exist_ok=True)
        self.metrics_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)

        # Initialize clients (lazy)
        self._clients: dict[str, BaseSocialClient] = {}

        # Rate limiter (5 posts per day across all platforms)
        self._rate_limiter = RateLimiter(
            max_calls=POSTS_PER_DAY,
            period=86400,  # 24 hours
        )

        # Circuit breakers per platform
        self._circuit_breakers: dict[str, CircuitBreaker] = {
            "facebook": CircuitBreaker(failure_threshold=3, reset_timeout=900),
            "instagram": CircuitBreaker(failure_threshold=3, reset_timeout=900),
            "twitter": CircuitBreaker(failure_threshold=3, reset_timeout=900),
        }

        # Logger
        self.logger = logging.getLogger("SocialMCP")

    def _get_client(self, platform: str) -> BaseSocialClient:
        """Get or create client for platform."""
        if platform not in self._clients:
            if platform == "facebook":
                self._clients[platform] = FacebookClient(dry_run=self.dry_run)
            elif platform == "instagram":
                self._clients[platform] = InstagramClient(dry_run=self.dry_run)
            elif platform == "twitter":
                self._clients[platform] = TwitterClient(dry_run=self.dry_run)
            else:
                raise ValueError(f"Unknown platform: {platform}")

        return self._clients[platform]

    def _log_action(self, action: str, details: dict[str, Any]) -> None:
        """Log an action to the daily log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_path / f"{today}.jsonl"

        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "component": "social_mcp",
            "action_type": action,
            "details": details,
        }

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

    def health(self) -> SocialResult:
        """
        Check health of all social media platforms.

        Returns:
            SocialResult with per-platform status
        """
        statuses = {}

        for platform in ["facebook", "instagram", "twitter"]:
            try:
                client = self._get_client(platform)
                cb = self._circuit_breakers[platform]

                statuses[platform] = {
                    "available": cb.can_execute(),
                    "authenticated": client.is_authenticated,
                    "dry_run": client.dry_run,
                }
            except Exception as e:
                statuses[platform] = {
                    "available": False,
                    "error": str(e),
                }

        self._log_action("health_check", {"statuses": statuses})

        return SocialResult(
            success=True,
            action="health",
            data=statuses,
        )

    def draft_post(
        self,
        platform: str,
        content: str,
        media_urls: Optional[list[str]] = None,
        hashtags: Optional[list[str]] = None,
        scheduled_for: Optional[datetime] = None,
    ) -> SocialResult:
        """
        Create a post draft for approval.

        Args:
            platform: Target platform (facebook, instagram, twitter)
            content: Post text content
            media_urls: Optional media attachments
            hashtags: Optional hashtags
            scheduled_for: Optional scheduled publish time

        Returns:
            SocialResult with draft info
        """
        try:
            # Validate platform
            platform_enum = Platform(platform.lower())
        except ValueError:
            return SocialResult(
                success=False,
                action="draft_post",
                error=f"Invalid platform: {platform}",
                error_type="validation_error",
            )

        # Create draft
        post = SocialPost(
            platform=platform_enum,
            status=PostStatus.DRAFT,
            content=content,
            media_urls=media_urls or [],
            hashtags=hashtags or [],
            scheduled_for=scheduled_for,
        )

        # Validate content
        errors = post.validate_for_platform()
        if errors:
            return SocialResult(
                success=False,
                action="draft_post",
                platform=platform,
                error="; ".join(errors),
                error_type="validation_error",
            )

        # Generate draft ID and save
        draft_id = f"{platform}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        post.draft_id = draft_id

        draft_path = self.drafts_path / f"{draft_id}.md"
        draft_path.write_text(post.to_markdown(), encoding="utf-8")

        self._log_action("draft_post", {
            "draft_id": draft_id,
            "platform": platform,
            "content_length": len(content),
        })

        return SocialResult(
            success=True,
            action="draft_post",
            platform=platform,
            draft_id=draft_id,
            data={
                "path": str(draft_path),
                "character_count": post.character_count,
                "character_limit": post.character_limit,
            },
        )

    def validate_post(
        self,
        platform: str,
        content: str,
        media_urls: Optional[list[str]] = None,
    ) -> SocialResult:
        """
        Validate content for a platform without creating a draft.

        Args:
            platform: Target platform
            content: Post text content
            media_urls: Optional media attachments

        Returns:
            SocialResult with validation status
        """
        try:
            client = self._get_client(platform)
            errors = client.validate_content(content, media_urls)

            return SocialResult(
                success=len(errors) == 0,
                action="validate_post",
                platform=platform,
                data={
                    "valid": len(errors) == 0,
                    "errors": errors,
                    "character_count": len(content),
                },
                error="; ".join(errors) if errors else None,
                error_type="validation_error" if errors else None,
            )

        except Exception as e:
            return SocialResult(
                success=False,
                action="validate_post",
                platform=platform,
                error=str(e),
                error_type="exception",
            )

    @requires_local
    def publish_post(
        self,
        draft_id: str,
        approval_id: str,
    ) -> SocialResult:
        """
        Publish an approved post.

        Args:
            draft_id: Draft ID to publish
            approval_id: HITL approval ID

        Returns:
            SocialResult with publication status
        """
        # Check rate limit
        if not self._rate_limiter.can_proceed():
            return SocialResult(
                success=False,
                action="publish_post",
                draft_id=draft_id,
                error="Daily post limit reached",
                error_type="rate_limit",
            )

        # Load draft
        draft_path = self.drafts_path / f"{draft_id}.md"
        if not draft_path.exists():
            return SocialResult(
                success=False,
                action="publish_post",
                draft_id=draft_id,
                error="Draft not found",
                error_type="not_found",
            )

        try:
            content = draft_path.read_text(encoding="utf-8")

            # Extract platform and content from draft
            platform = None
            post_content = ""

            for line in content.split("\n"):
                if line.startswith("platform:"):
                    platform = line.split(":")[1].strip()
                elif line.startswith("## Content"):
                    # Next non-empty lines are content
                    idx = content.index("## Content")
                    content_section = content[idx:].split("##")[1] if "##" in content[idx+1:] else content[idx:]
                    post_content = content_section.replace("## Content", "").strip()
                    break

            if not platform:
                return SocialResult(
                    success=False,
                    action="publish_post",
                    draft_id=draft_id,
                    error="Could not determine platform from draft",
                    error_type="parse_error",
                )

            # Check circuit breaker
            cb = self._circuit_breakers.get(platform)
            if cb and not cb.can_execute():
                return SocialResult(
                    success=False,
                    action="publish_post",
                    draft_id=draft_id,
                    platform=platform,
                    error="Platform circuit breaker open",
                    error_type="circuit_breaker",
                )

            # Get client and publish
            client = self._get_client(platform)
            if not client.is_authenticated:
                client.authenticate()

            result = client.create_post(post_content)

            if result.success:
                cb.record_success() if cb else None

                # Move draft to Done folder
                done_path = self.vault_path / "Done" / draft_path.name
                draft_path.rename(done_path)

                self._log_action("publish_post", {
                    "draft_id": draft_id,
                    "platform": platform,
                    "post_id": result.post_id,
                    "approval_id": approval_id,
                })

                return SocialResult(
                    success=True,
                    action="publish_post",
                    platform=platform,
                    draft_id=draft_id,
                    post_id=result.post_id,
                    post_url=result.post_url,
                )
            else:
                cb.record_failure() if cb else None

                return SocialResult(
                    success=False,
                    action="publish_post",
                    draft_id=draft_id,
                    platform=platform,
                    error=result.error,
                    error_type=result.error_type,
                )

        except Exception as e:
            self._log_action("publish_post_error", {
                "draft_id": draft_id,
                "error": str(e),
            })
            return SocialResult(
                success=False,
                action="publish_post",
                draft_id=draft_id,
                error=str(e),
                error_type="exception",
            )

    def get_engagement(
        self,
        platform: str,
        post_id: str,
    ) -> SocialResult:
        """
        Get engagement metrics for a published post.

        Args:
            platform: Platform name
            post_id: Platform-specific post ID

        Returns:
            SocialResult with engagement data
        """
        try:
            client = self._get_client(platform)
            result = client.get_engagement(post_id)

            if result.success:
                # Save metrics to vault
                metrics_file = self.metrics_path / f"{platform}_{post_id}.md"
                metrics_content = f"""---
type: engagement
platform: {platform}
post_id: "{post_id}"
fetched_at: {datetime.utcnow().isoformat()}
---

# Engagement: {platform} - {post_id}

## Metrics

{json.dumps(result.details, indent=2)}

---

[Fetched by SocialMCP]
"""
                metrics_file.write_text(metrics_content, encoding="utf-8")

                self._log_action("get_engagement", {
                    "platform": platform,
                    "post_id": post_id,
                    "metrics": result.details,
                })

            return SocialResult(
                success=result.success,
                action="get_engagement",
                platform=platform,
                post_id=post_id,
                data=result.details,
                error=result.error,
                error_type=result.error_type,
            )

        except Exception as e:
            return SocialResult(
                success=False,
                action="get_engagement",
                platform=platform,
                post_id=post_id,
                error=str(e),
                error_type="exception",
            )

    def platform_status(self, platform: str) -> SocialResult:
        """
        Get detailed status for a specific platform.

        Args:
            platform: Platform name

        Returns:
            SocialResult with platform status
        """
        try:
            client = self._get_client(platform)
            cb = self._circuit_breakers.get(platform)

            status = client.health_check()
            status["circuit_breaker"] = {
                "state": "open" if (cb and not cb.can_execute()) else "closed",
            }

            return SocialResult(
                success=True,
                action="platform_status",
                platform=platform,
                data=status,
            )

        except Exception as e:
            return SocialResult(
                success=False,
                action="platform_status",
                platform=platform,
                error=str(e),
                error_type="exception",
            )

    def get_status(self) -> dict[str, Any]:
        """Get MCP server status."""
        return {
            "name": "SocialMCP",
            "dry_run": self.dry_run,
            "rate_limiter": {
                "remaining": self._rate_limiter.remaining_calls,
                "period": "daily",
            },
            "platforms": list(self._circuit_breakers.keys()),
            "vault_path": str(self.vault_path),
        }
