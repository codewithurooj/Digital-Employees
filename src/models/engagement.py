"""Engagement model for social media metrics tracking."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, computed_field

from .social_post import Platform


class EngagementMetrics(BaseModel):
    """Platform-specific engagement metrics."""

    # Universal metrics
    impressions: int = Field(ge=0, default=0)
    reach: int = Field(ge=0, default=0)
    likes: int = Field(ge=0, default=0)
    comments: int = Field(ge=0, default=0)

    # Platform-specific
    shares: int = Field(ge=0, default=0)  # Facebook
    saves: int = Field(ge=0, default=0)  # Instagram
    retweets: int = Field(ge=0, default=0)  # Twitter
    quote_tweets: int = Field(ge=0, default=0)  # Twitter
    replies: int = Field(ge=0, default=0)  # Twitter
    video_views: int = Field(ge=0, default=0)  # Video content

    @computed_field
    @property
    def total_interactions(self) -> int:
        """Calculate total interactions."""
        return (
            self.likes
            + self.comments
            + self.shares
            + self.saves
            + self.retweets
            + self.quote_tweets
            + self.replies
        )

    @computed_field
    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate as percentage."""
        if self.reach == 0:
            return 0.0
        return round((self.total_interactions / self.reach) * 100, 2)


class TopComment(BaseModel):
    """Notable comment on a post."""
    author: str
    content: str
    likes: int = 0
    timestamp: Optional[datetime] = None


class Engagement(BaseModel):
    """Social media engagement metrics for a published post."""

    # Post identifiers
    platform: Platform
    post_id: str
    source_draft: Optional[str] = None  # Link to original draft file

    # Timestamps
    published_at: datetime
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    # Metrics
    metrics: EngagementMetrics = Field(default_factory=EngagementMetrics)

    # Historical tracking (24h changes)
    metrics_24h_ago: Optional[EngagementMetrics] = None

    # Top comments
    top_comments: list[TopComment] = Field(default_factory=list, max_length=5)

    def calculate_trend(self, metric_name: str) -> str:
        """Calculate 24h trend for a metric."""
        if not self.metrics_24h_ago:
            return "N/A (new post)"

        current = getattr(self.metrics, metric_name, 0)
        previous = getattr(self.metrics_24h_ago, metric_name, 0)

        if previous == 0:
            return f"+{current}" if current > 0 else "0"

        change = current - previous
        pct_change = (change / previous) * 100

        if change > 0:
            return f"+{change} (+{pct_change:.1f}%)"
        elif change < 0:
            return f"{change} ({pct_change:.1f}%)"
        return "0 (no change)"

    def to_markdown(self) -> str:
        """Convert engagement to vault markdown format."""
        m = self.metrics

        # Platform-specific metrics rows
        platform_metrics = ""
        if self.platform == Platform.FACEBOOK:
            platform_metrics = f"| Shares | {m.shares:,} |"
        elif self.platform == Platform.INSTAGRAM:
            platform_metrics = f"| Saves | {m.saves:,} |"
        elif self.platform == Platform.TWITTER:
            platform_metrics = f"""| Retweets | {m.retweets:,} |
| Quote Tweets | {m.quote_tweets:,} |
| Replies | {m.replies:,} |"""

        # Trend section
        trend_section = ""
        if self.metrics_24h_ago:
            trend_section = f"""## Trend (24h)

- Likes: {self.calculate_trend('likes')}
- Comments: {self.calculate_trend('comments')}
- {'Shares' if self.platform == Platform.FACEBOOK else 'Saves' if self.platform == Platform.INSTAGRAM else 'Retweets'}: {self.calculate_trend('shares' if self.platform == Platform.FACEBOOK else 'saves' if self.platform == Platform.INSTAGRAM else 'retweets')}
"""
        else:
            trend_section = """## Trend (24h)

*New post - trend data will be available after 24 hours*
"""

        # Top comments section
        comments_section = ""
        if self.top_comments:
            comments_section = "## Top Comments\n\n" + "\n".join([
                f'> "{c.content}" - {c.author}'
                for c in self.top_comments[:5]
            ])

        return f"""---
type: engagement
platform: {self.platform.value}
post_id: "{self.post_id}"
source_draft: "{self.source_draft or ''}"
published_at: {self.published_at.isoformat()}
last_updated: {self.last_updated.isoformat()}
metrics:
  impressions: {m.impressions}
  reach: {m.reach}
  likes: {m.likes}
  comments: {m.comments}
  shares: {m.shares}
  saves: {m.saves}
  retweets: {m.retweets}
  quote_tweets: {m.quote_tweets}
  engagement_rate: {m.engagement_rate}
---

# Engagement Report: {self.platform.value.title()} Post

**Post ID**: {self.post_id}
**Published**: {self.published_at.strftime('%Y-%m-%d %I:%M %p')}
**Last Updated**: {self.last_updated.strftime('%Y-%m-%d %I:%M %p')}

## Metrics

| Metric | Value |
|--------|-------|
| Impressions | {m.impressions:,} |
| Reach | {m.reach:,} |
| Likes | {m.likes:,} |
| Comments | {m.comments:,} |
{platform_metrics}
| **Engagement Rate** | {m.engagement_rate}% |

{trend_section}

{comments_section}

---

[Fetched from {self.platform.value.title()} API]
"""

    @property
    def vault_filename(self) -> str:
        """Generate vault filename for this engagement report."""
        return f"{self.platform.value}_{self.post_id}.md"
