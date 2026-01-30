"""SocialPost model for multi-platform social media integration."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Platform(str, Enum):
    """Supported social media platforms."""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"


class PostStatus(str, Enum):
    """Post lifecycle status."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PUBLISHED = "published"
    FAILED = "failed"


class ContentType(str, Enum):
    """Type of social media content."""
    TEXT = "text"
    IMAGE = "image"
    CAROUSEL = "carousel"
    VIDEO = "video"


# Platform character limits
PLATFORM_LIMITS = {
    Platform.FACEBOOK: 63206,
    Platform.INSTAGRAM: 2200,
    Platform.TWITTER: 280,
}


class SocialPost(BaseModel):
    """Social media post draft and published state."""

    # Platform info
    platform: Platform
    status: PostStatus = PostStatus.DRAFT

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    scheduled_for: Optional[datetime] = None
    published_at: Optional[datetime] = None

    # Content
    content: str
    content_type: ContentType = ContentType.TEXT
    media_urls: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)

    # Approval workflow
    approval_id: Optional[str] = None

    # Platform-specific IDs
    post_id: Optional[str] = None  # Set after publishing
    draft_id: Optional[str] = None  # Internal draft ID

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        """Ensure content is not empty."""
        if not v.strip():
            raise ValueError("Content cannot be empty")
        return v

    def validate_for_platform(self) -> list[str]:
        """Validate content against platform-specific rules."""
        errors = []

        # Check character limit
        limit = PLATFORM_LIMITS[self.platform]
        if len(self.content) > limit:
            errors.append(f"Content exceeds {self.platform.value} limit of {limit} characters (current: {len(self.content)})")

        # Instagram requires media
        if self.platform == Platform.INSTAGRAM and not self.media_urls:
            errors.append("Instagram posts require at least one media attachment")

        # Check hashtag count (Instagram recommends max 30)
        if self.platform == Platform.INSTAGRAM and len(self.hashtags) > 30:
            errors.append("Instagram allows maximum 30 hashtags")

        return errors

    @property
    def character_count(self) -> int:
        """Return current character count."""
        return len(self.content)

    @property
    def character_limit(self) -> int:
        """Return platform character limit."""
        return PLATFORM_LIMITS[self.platform]

    @property
    def is_valid(self) -> bool:
        """Check if post passes all validations."""
        return len(self.validate_for_platform()) == 0

    def to_markdown(self) -> str:
        """Convert post to vault markdown format."""
        validation_checks = self.validate_for_platform()
        validation_status = "All checks passed" if not validation_checks else "\n".join([f"- [ ] {e}" for e in validation_checks])

        hashtag_display = " ".join([f"#{tag}" if not tag.startswith("#") else tag for tag in self.hashtags])

        return f"""---
type: social_post
platform: {self.platform.value}
status: {self.status.value}
created_at: {self.created_at.isoformat()}
scheduled_for: {self.scheduled_for.isoformat() if self.scheduled_for else "null"}
approval_id: {self.approval_id or "null"}
post_id: {self.post_id or "null"}
content_type: {self.content_type.value}
media_urls: {self.media_urls}
hashtags: {self.hashtags}
mentions: {self.mentions}
---

# Social Post Draft

**Platform**: {self.platform.value.title()}
**Type**: {self.content_type.value.title()} Post
**Created**: {self.created_at.strftime('%Y-%m-%d %I:%M %p')}

## Content

{self.content}

{hashtag_display}

## Validation

- [{'x' if self.is_valid else ' '}] Character count: {self.character_count}/{self.character_limit} ({self.platform.value.title()} limit)
{validation_status if validation_checks else '- [x] No prohibited content detected'}

## Approval

Status: {self.status.value.replace('_', ' ').title()}

---

[Created by social_posting skill]
"""

    @property
    def vault_filename(self) -> str:
        """Generate vault filename for this post."""
        timestamp = self.created_at.strftime("%Y%m%d%H%M%S")
        return f"{self.platform.value}_{timestamp}.md"
