"""
Social Posting Skill - Multi-platform social media posting with approval workflow.

This skill provides content creation, validation, and posting
for Facebook, Instagram, and Twitter with HITL approval integration.

Usage:
    from src.skills import SocialPostingSkill

    skill = SocialPostingSkill(vault_path='./AI_Employee_Vault')

    # Create a draft
    result = skill.create_draft('facebook', 'Hello world!')

    # Request approval
    approval_id = skill.request_approval(draft_id)

    # Publish after approval
    result = skill.publish(draft_id, approval_id)

Features:
- Multi-platform support (Facebook, Instagram, Twitter)
- Content validation per platform
- Draft management in vault
- HITL approval integration
- Engagement tracking
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.mcp_servers.social_mcp import SocialMCP, SocialResult
from src.models import Platform, PostStatus, SocialPost


class SocialPostingSkill:
    """
    Skill for multi-platform social media posting.

    Provides a high-level interface for creating, validating,
    approving, and publishing social media posts.
    """

    def __init__(
        self,
        vault_path: str,
        dry_run: bool = True,
    ):
        """
        Initialize Social Posting skill.

        Args:
            vault_path: Path to the Obsidian vault
            dry_run: If True, don't actually post to platforms
        """
        self.vault_path = Path(vault_path)
        self.dry_run = dry_run

        # Initialize MCP server
        self._mcp = SocialMCP(
            vault_path=str(vault_path),
            dry_run=dry_run,
        )

        # Vault paths
        self.drafts_path = self.vault_path / "Social" / "Drafts"
        self.pending_path = self.vault_path / "Pending_Approval"

        # Logger
        self.logger = logging.getLogger("SocialPostingSkill")

    def create_draft(
        self,
        platform: str,
        content: str,
        media_urls: Optional[list[str]] = None,
        hashtags: Optional[list[str]] = None,
        scheduled_for: Optional[datetime] = None,
    ) -> SocialResult:
        """
        Create a post draft.

        Args:
            platform: Target platform (facebook, instagram, twitter)
            content: Post text content
            media_urls: Optional media attachments
            hashtags: Optional hashtags
            scheduled_for: Optional scheduled publish time

        Returns:
            SocialResult with draft info
        """
        return self._mcp.draft_post(
            platform=platform,
            content=content,
            media_urls=media_urls,
            hashtags=hashtags,
            scheduled_for=scheduled_for,
        )

    def validate_content(
        self,
        platform: str,
        content: str,
        media_urls: Optional[list[str]] = None,
    ) -> SocialResult:
        """
        Validate content for a platform.

        Args:
            platform: Target platform
            content: Post text content
            media_urls: Optional media attachments

        Returns:
            SocialResult with validation status
        """
        return self._mcp.validate_post(
            platform=platform,
            content=content,
            media_urls=media_urls,
        )

    def request_approval(self, draft_id: str) -> Optional[str]:
        """
        Request human approval for a draft.

        Creates an approval file in Pending_Approval folder.

        Args:
            draft_id: Draft ID to request approval for

        Returns:
            Approval ID if created, None on error
        """
        # Load draft
        draft_path = self.drafts_path / f"{draft_id}.md"
        if not draft_path.exists():
            self.logger.error(f"Draft not found: {draft_id}")
            return None

        try:
            content = draft_path.read_text(encoding="utf-8")

            # Create approval request
            approval_id = f"APR-{datetime.utcnow().strftime('%Y%m%d')}-{hash(draft_id) % 1000:03d}"

            approval_content = f"""---
type: social_post_approval
approval_id: "{approval_id}"
draft_id: "{draft_id}"
status: pending
created_at: {datetime.utcnow().isoformat()}
---

# Social Post Approval Request

**Approval ID**: {approval_id}
**Draft ID**: {draft_id}
**Status**: Pending

## Draft Content

{content}

## Actions

- [ ] Review post content
- [ ] Verify platform appropriateness
- [ ] **APPROVE** or **REJECT**

To approve: Move this file to `Approved/` folder
To reject: Move this file to `Rejected/` folder

---

*Created by SocialPostingSkill*
"""

            approval_path = self.pending_path / f"{approval_id}.md"
            self.pending_path.mkdir(parents=True, exist_ok=True)
            approval_path.write_text(approval_content, encoding="utf-8")

            # Update draft status
            updated_draft = content.replace("status: draft", "status: pending_approval")
            updated_draft = updated_draft.replace(f"approval_id: null", f'approval_id: "{approval_id}"')
            draft_path.write_text(updated_draft, encoding="utf-8")

            self.logger.info(f"Created approval request {approval_id} for draft {draft_id}")
            return approval_id

        except Exception as e:
            self.logger.error(f"Failed to create approval request: {e}")
            return None

    def check_approval_status(self, approval_id: str) -> str:
        """
        Check status of an approval request.

        Args:
            approval_id: Approval ID to check

        Returns:
            Status string: 'pending', 'approved', 'rejected', or 'not_found'
        """
        # Check Pending_Approval
        pending = self.pending_path / f"{approval_id}.md"
        if pending.exists():
            return "pending"

        # Check Approved
        approved = self.vault_path / "Approved" / f"{approval_id}.md"
        if approved.exists():
            return "approved"

        # Check Rejected
        rejected = self.vault_path / "Rejected" / f"{approval_id}.md"
        if rejected.exists():
            return "rejected"

        return "not_found"

    def publish(
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
        # Verify approval
        status = self.check_approval_status(approval_id)
        if status != "approved":
            return SocialResult(
                success=False,
                action="publish",
                draft_id=draft_id,
                error=f"Approval status is '{status}', expected 'approved'",
                error_type="approval_error",
            )

        return self._mcp.publish_post(
            draft_id=draft_id,
            approval_id=approval_id,
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
        return self._mcp.get_engagement(
            platform=platform,
            post_id=post_id,
        )

    def get_drafts(self) -> list[dict[str, Any]]:
        """
        List all draft posts.

        Returns:
            List of draft info dictionaries
        """
        drafts = []

        if self.drafts_path.exists():
            for file_path in self.drafts_path.glob("*.md"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                    drafts.append({
                        "draft_id": file_path.stem,
                        "path": str(file_path),
                        "size": len(content),
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    })
                except Exception as e:
                    self.logger.warning(f"Error reading draft {file_path}: {e}")

        return drafts

    def get_platform_limits(self) -> dict[str, dict[str, Any]]:
        """
        Get character limits and rules for each platform.

        Returns:
            Dict with platform limits
        """
        return {
            "facebook": {
                "character_limit": 63206,
                "requires_media": False,
                "hashtag_limit": None,
            },
            "instagram": {
                "character_limit": 2200,
                "requires_media": True,
                "hashtag_limit": 30,
            },
            "twitter": {
                "character_limit": 280,
                "requires_media": False,
                "hashtag_limit": None,
            },
        }

    def get_status(self) -> dict[str, Any]:
        """Get skill status."""
        return {
            "name": "SocialPostingSkill",
            "dry_run": self.dry_run,
            "draft_count": len(self.get_drafts()),
            "mcp_status": self._mcp.get_status(),
        }
