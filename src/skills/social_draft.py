"""Social Media Draft Skill - Create and schedule social media drafts.

Cloud agent uses this to create draft social posts in Pending_Approval/social/
for the local agent to review and publish.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = {"facebook", "instagram", "twitter"}

PLATFORM_CHAR_LIMITS = {
    "twitter": 280,
    "facebook": 63206,
    "instagram": 2200,
}


class SocialDraftSkill:
    """Skill for creating social media draft posts."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.pending_social_path = self.vault_path / "Pending_Approval" / "social"
        self.calendar_path = self.vault_path / "Social" / "Calendar"
        self.logs_path = self.vault_path / "Logs"

        self.pending_social_path.mkdir(parents=True, exist_ok=True)
        self.calendar_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)

    def create_draft(
        self,
        platform: str,
        content: str,
        hashtags: Optional[list[str]] = None,
        media_urls: Optional[list[str]] = None,
        scheduled_for: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """Create a social media draft post.

        Args:
            platform: Target platform (facebook, instagram, twitter)
            content: Post content text
            hashtags: Optional list of hashtags
            media_urls: Optional list of media URLs
            scheduled_for: Optional scheduled publish time

        Returns:
            Dict with success, draft_path, etc.
        """
        platform = platform.lower()

        if platform not in SUPPORTED_PLATFORMS:
            return {
                "success": False,
                "error": f"Unsupported platform: {platform}. Supported: {', '.join(sorted(SUPPORTED_PLATFORMS))}",
            }

        char_limit = PLATFORM_CHAR_LIMITS.get(platform, 5000)
        full_content = content
        if hashtags:
            full_content += " " + " ".join(hashtags)

        if len(full_content) > char_limit:
            return {
                "success": False,
                "error": f"Content exceeds {platform} limit of {char_limit} characters (got {len(full_content)})",
            }

        if not content.strip():
            return {
                "success": False,
                "error": "Content cannot be empty",
            }

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        draft_id = f"{platform}_{timestamp}"
        filename = f"{draft_id}.md"

        scheduled_str = scheduled_for.isoformat() if scheduled_for else "immediate"

        draft_content = f"""---
type: social_draft
platform: {platform}
draft_id: "{draft_id}"
status: pending_approval
scheduled_for: {scheduled_str}
created_at: {datetime.now().isoformat()}
source_agent: cloud
requires_local_action: true
---

# Social Media Draft: {platform.title()}

**Platform**: {platform}
**Status**: Pending Approval
**Scheduled**: {scheduled_str}

## Content

{content}

"""
        if hashtags:
            draft_content += f"## Hashtags\n\n{' '.join(hashtags)}\n\n"

        if media_urls:
            draft_content += "## Media\n\n"
            for url in media_urls:
                draft_content += f"- {url}\n"
            draft_content += "\n"

        draft_content += f"""## Character Count

- Content: {len(content)} / {char_limit}
- With hashtags: {len(full_content)} / {char_limit}

## Action Required

- [ ] Review post content
- [ ] Approve for publishing
- [ ] Local agent will publish via SocialMCP

---
*Drafted by Cloud Agent at {datetime.now().isoformat()}*
"""

        draft_path = self.pending_social_path / filename
        draft_path.write_text(draft_content, encoding="utf-8")

        if scheduled_for:
            cal_path = self.calendar_path / filename
            cal_path.write_text(draft_content, encoding="utf-8")

        self._log_action("create_draft", {
            "draft_id": draft_id,
            "platform": platform,
            "content_length": len(content),
            "has_hashtags": bool(hashtags),
            "scheduled": scheduled_str,
        })

        return {
            "success": True,
            "draft_id": draft_id,
            "draft_path": str(draft_path),
            "platform": platform,
            "character_count": len(full_content),
            "character_limit": char_limit,
        }

    def get_upcoming_posts(self, within_minutes: int = 60) -> list[dict[str, Any]]:
        """Get posts scheduled within the next N minutes.

        Args:
            within_minutes: Look ahead window in minutes

        Returns:
            List of upcoming post dicts
        """
        upcoming = []
        now = datetime.now()
        cutoff = now + timedelta(minutes=within_minutes)

        for draft_file in self.pending_social_path.glob("*.md"):
            content = draft_file.read_text(encoding="utf-8")
            for line in content.split("\n"):
                if line.startswith("scheduled_for:"):
                    sched_str = line.split(":", 1)[1].strip()
                    if sched_str == "immediate":
                        upcoming.append({
                            "file": str(draft_file),
                            "scheduled_for": "immediate",
                        })
                    else:
                        try:
                            sched_time = datetime.fromisoformat(sched_str)
                            if now <= sched_time <= cutoff:
                                upcoming.append({
                                    "file": str(draft_file),
                                    "scheduled_for": sched_str,
                                })
                        except ValueError:
                            pass
                    break

        return upcoming

    def _log_action(self, action: str, details: dict[str, Any]) -> None:
        """Log action to daily log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_path / f"{today}.jsonl"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "component": "social_draft",
            "action": action,
            "details": details,
        }

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
