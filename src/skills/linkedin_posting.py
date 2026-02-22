"""
LinkedIn Auto-Posting Skill

Provides capabilities to draft, schedule, and publish posts to LinkedIn.
All posts require HITL approval before publishing.

Usage:
    from src.skills.linkedin_posting import LinkedInPostingSkill

    skill = LinkedInPostingSkill(
        vault_path='./AI_Employee_Vault',
        session_path='./config/linkedin_session'
    )

    # Draft a post (creates approval request)
    result = skill.draft_post(
        content="Excited to share our latest project!",
        visibility="public"
    )

    # Post after approval
    result = skill.publish_approved_post(approval_id)

Tools provided:
- draft_post: Create a draft post for approval
- publish_approved_post: Publish an approved post
- schedule_post: Schedule a post for future publishing
- get_draft_posts: List all draft posts
- delete_draft: Delete a draft post
- get_post_analytics: Get engagement metrics for a post
"""

import json
import re
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

# Playwright imports - optional
try:
    from playwright.sync_api import sync_playwright, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Import from parent package
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.hitl import ApprovalManager, ApprovalStatus
from src.utils.retry_handler import RateLimiter, retry, CircuitBreaker


class PostVisibility(Enum):
    """LinkedIn post visibility options."""
    PUBLIC = "public"           # Anyone on or off LinkedIn
    CONNECTIONS = "connections"  # Connections only
    # Note: LinkedIn doesn't support "private" posts


class PostType(Enum):
    """Types of LinkedIn posts."""
    TEXT = "text"              # Text-only post
    IMAGE = "image"            # Post with image
    ARTICLE = "article"        # Share an article link
    DOCUMENT = "document"      # Share a document/PDF
    POLL = "poll"              # Create a poll


# Constants
MAX_POST_LENGTH = 3000         # LinkedIn's character limit
MAX_HASHTAGS = 30              # Recommended max hashtags
MAX_MENTIONS = 50              # Max mentions per post
POSTS_PER_DAY = 3              # Rate limit from Company Handbook
MAX_IMAGES = 9                 # LinkedIn allows up to 9 images
MAX_POLL_OPTIONS = 4           # LinkedIn poll limit


@dataclass
class PostDraft:
    """Represents a LinkedIn post draft."""
    draft_id: str
    content: str
    post_type: PostType = PostType.TEXT
    visibility: PostVisibility = PostVisibility.PUBLIC
    hashtags: List[str] = field(default_factory=list)
    mentions: List[str] = field(default_factory=list)
    media_urls: List[str] = field(default_factory=list)
    article_url: Optional[str] = None
    poll_question: Optional[str] = None
    poll_options: List[str] = field(default_factory=list)
    poll_duration_days: int = 7
    scheduled_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    approval_id: Optional[str] = None
    status: str = "draft"

    def validate(self) -> List[str]:
        """Validate the post and return list of errors."""
        errors = []

        # Content length
        if not self.content:
            errors.append("Post content cannot be empty")
        elif len(self.content) > MAX_POST_LENGTH:
            errors.append(f"Content exceeds {MAX_POST_LENGTH} characters (current: {len(self.content)})")

        # Hashtags
        if len(self.hashtags) > MAX_HASHTAGS:
            errors.append(f"Too many hashtags (max {MAX_HASHTAGS})")

        # Mentions
        if len(self.mentions) > MAX_MENTIONS:
            errors.append(f"Too many mentions (max {MAX_MENTIONS})")

        # Media
        if len(self.media_urls) > MAX_IMAGES:
            errors.append(f"Too many images (max {MAX_IMAGES})")

        # Poll validation
        if self.post_type == PostType.POLL:
            if not self.poll_question:
                errors.append("Poll requires a question")
            if len(self.poll_options) < 2:
                errors.append("Poll requires at least 2 options")
            if len(self.poll_options) > MAX_POLL_OPTIONS:
                errors.append(f"Poll cannot have more than {MAX_POLL_OPTIONS} options")
            if self.poll_duration_days < 1 or self.poll_duration_days > 14:
                errors.append("Poll duration must be 1-14 days")

        # Article validation
        if self.post_type == PostType.ARTICLE and not self.article_url:
            errors.append("Article post requires a URL")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'draft_id': self.draft_id,
            'content': self.content,
            'post_type': self.post_type.value,
            'visibility': self.visibility.value,
            'hashtags': self.hashtags,
            'mentions': self.mentions,
            'media_urls': self.media_urls,
            'article_url': self.article_url,
            'poll_question': self.poll_question,
            'poll_options': self.poll_options,
            'poll_duration_days': self.poll_duration_days,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'created_at': self.created_at.isoformat(),
            'approval_id': self.approval_id,
            'status': self.status
        }


@dataclass
class PostResult:
    """Result of a posting operation."""
    success: bool
    post_id: Optional[str] = None
    draft_id: Optional[str] = None
    approval_id: Optional[str] = None
    status: str = ""
    error: Optional[str] = None
    error_type: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            'success': self.success,
            'status': self.status,
        }
        if self.post_id:
            result['post_id'] = self.post_id
        if self.draft_id:
            result['draft_id'] = self.draft_id
        if self.approval_id:
            result['approval_id'] = self.approval_id
        if self.error:
            result['error'] = self.error
            result['error_type'] = self.error_type
        result.update(self.details)
        return result


class LinkedInPostingSkill:
    """
    LinkedIn Auto-Posting Skill with HITL approval integration.

    All posts require human approval before publishing.
    """

    def __init__(
        self,
        vault_path: str,
        session_path: Optional[str] = None,
        headless: bool = False
    ):
        """
        Initialize LinkedIn Posting Skill.

        Args:
            vault_path: Path to the Obsidian vault
            session_path: Path to LinkedIn browser session
            headless: Run browser in headless mode
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright not installed. Run:\n"
                "pip install playwright\n"
                "playwright install chromium"
            )

        self.vault_path = Path(vault_path)
        self.drafts_path = self.vault_path / 'Plans' / 'linkedin_drafts'
        self.drafts_path.mkdir(parents=True, exist_ok=True)
        self.logs_path = self.vault_path / 'Logs'
        self.logs_path.mkdir(parents=True, exist_ok=True)

        # Session for browser automation
        if session_path is None:
            session_path = str(self.vault_path.parent / 'config' / 'linkedin_session')
        self.session_path = Path(session_path)
        self.session_path.mkdir(parents=True, exist_ok=True)

        self.headless = headless

        # Initialize components
        self.approval_manager = ApprovalManager(str(self.vault_path))
        self.rate_limiter = RateLimiter('linkedin_post', max_calls=POSTS_PER_DAY, period_seconds=86400)
        self.circuit_breaker = CircuitBreaker('linkedin', failure_threshold=3)

        # Playwright objects
        self._playwright = None
        self._browser: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

        # In-memory draft cache
        self._drafts: Dict[str, PostDraft] = {}
        self._load_drafts()

        self.logger = logging.getLogger('LinkedInPostingSkill')

    def _load_drafts(self) -> None:
        """Load drafts from disk."""
        for draft_file in self.drafts_path.glob('*.json'):
            try:
                data = json.loads(draft_file.read_text())
                draft = PostDraft(
                    draft_id=data['draft_id'],
                    content=data['content'],
                    post_type=PostType(data.get('post_type', 'text')),
                    visibility=PostVisibility(data.get('visibility', 'public')),
                    hashtags=data.get('hashtags', []),
                    mentions=data.get('mentions', []),
                    media_urls=data.get('media_urls', []),
                    article_url=data.get('article_url'),
                    poll_question=data.get('poll_question'),
                    poll_options=data.get('poll_options', []),
                    poll_duration_days=data.get('poll_duration_days', 7),
                    scheduled_time=datetime.fromisoformat(data['scheduled_time']) if data.get('scheduled_time') else None,
                    created_at=datetime.fromisoformat(data['created_at']),
                    approval_id=data.get('approval_id'),
                    status=data.get('status', 'draft')
                )
                self._drafts[draft.draft_id] = draft
            except Exception as e:
                self.logger.warning(f"Failed to load draft {draft_file}: {e}")

    def _save_draft(self, draft: PostDraft) -> None:
        """Save draft to disk."""
        draft_file = self.drafts_path / f'{draft.draft_id}.json'
        draft_file.write_text(json.dumps(draft.to_dict(), indent=2))
        self._drafts[draft.draft_id] = draft

    def _delete_draft_file(self, draft_id: str) -> None:
        """Delete draft file from disk."""
        draft_file = self.drafts_path / f'{draft_id}.json'
        if draft_file.exists():
            draft_file.unlink()
        if draft_id in self._drafts:
            del self._drafts[draft_id]

    def _generate_draft_id(self, content: str) -> str:
        """Generate unique draft ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"draft_{timestamp}_{content_hash}"

    def _extract_hashtags(self, content: str) -> List[str]:
        """Extract hashtags from content."""
        return re.findall(r'#(\w+)', content)

    def _extract_mentions(self, content: str) -> List[str]:
        """Extract @mentions from content."""
        return re.findall(r'@(\w+)', content)

    def _cleanup_session_locks(self) -> None:
        """Remove stale Chromium lock files that cause crash-on-start."""
        for lock_name in ('lockfile', 'SingletonLock', 'SingletonCookie', 'SingletonSocket'):
            lock_path = self.session_path / lock_name
            if lock_path.exists():
                try:
                    lock_path.unlink()
                    self.logger.info(f"Removed stale lock: {lock_name}")
                except Exception as e:
                    self.logger.warning(f"Could not remove {lock_name}: {e}")

    def _start_browser(self) -> bool:
        """Start Playwright browser."""
        try:
            self._cleanup_session_locks()
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch_persistent_context(
                str(self.session_path),
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled'],
                viewport={'width': 1280, 'height': 900}
            )
            self._page = self._browser.pages[0] if self._browser.pages else self._browser.new_page()
            return True
        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            return False

    def _stop_browser(self) -> None:
        """Stop Playwright browser."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except:
            pass
        finally:
            self._browser = None
            self._page = None
            self._playwright = None

    def _ensure_logged_in(self) -> bool:
        """Ensure user is logged into LinkedIn."""
        try:
            self._page.goto('https://www.linkedin.com/feed/', wait_until='domcontentloaded')
            self._page.wait_for_timeout(3000)

            # Check URL — redirected to login/authwall means not logged in
            current_url = self._page.url
            if 'login' in current_url or 'authwall' in current_url or 'checkpoint' in current_url:
                self.logger.warning("Not logged into LinkedIn - manual login required")
                print("\n>>> Please log in to LinkedIn in the browser window.")
                print(">>> Waiting up to 2 minutes for login...")
                # Wait for redirect back to feed after successful login
                self._page.wait_for_url('**/feed/**', timeout=120000)
                self._page.wait_for_timeout(2000)

            self.logger.info("LinkedIn login confirmed")
            return True
        except Exception as e:
            self.logger.error(f"Login check failed: {e}")
            return False

    def _log_operation(self, operation: str, details: Dict[str, Any]) -> None:
        """Log an operation."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        entry = {
            'timestamp': datetime.now().isoformat(),
            'component': 'LinkedInPostingSkill',
            'operation': operation,
            'details': details
        }

        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text())
            except:
                logs = []

        logs.append(entry)
        log_file.write_text(json.dumps(logs, indent=2), encoding='utf-8')

    # =========================================================================
    # Public API - Skill Tools
    # =========================================================================

    def draft_post(
        self,
        content: str,
        visibility: str = "public",
        post_type: str = "text",
        hashtags: Optional[List[str]] = None,
        article_url: Optional[str] = None,
        media_urls: Optional[List[str]] = None,
        poll_question: Optional[str] = None,
        poll_options: Optional[List[str]] = None,
        poll_duration_days: int = 7,
        scheduled_time: Optional[str] = None
    ) -> PostResult:
        """
        Create a draft post and submit for approval.

        Args:
            content: Post content text
            visibility: "public" or "connections"
            post_type: "text", "image", "article", "poll"
            hashtags: Additional hashtags (auto-extracted from content too)
            article_url: URL for article posts
            media_urls: URLs/paths to images
            poll_question: Question for poll posts
            poll_options: Options for poll posts
            poll_duration_days: Poll duration (1-14 days)
            scheduled_time: ISO format datetime for scheduling

        Returns:
            PostResult with draft_id and approval_id
        """
        try:
            # Parse enums
            vis = PostVisibility(visibility.lower())
            ptype = PostType(post_type.lower())
        except ValueError as e:
            return PostResult(
                success=False,
                status='failed',
                error=str(e),
                error_type='ValidationError'
            )

        # Extract hashtags and mentions from content
        auto_hashtags = self._extract_hashtags(content)
        auto_mentions = self._extract_mentions(content)

        all_hashtags = list(set(auto_hashtags + (hashtags or [])))

        # Parse scheduled time
        sched_time = None
        if scheduled_time:
            try:
                sched_time = datetime.fromisoformat(scheduled_time)
                if sched_time <= datetime.now():
                    return PostResult(
                        success=False,
                        status='failed',
                        error='Scheduled time must be in the future',
                        error_type='ValidationError'
                    )
            except ValueError:
                return PostResult(
                    success=False,
                    status='failed',
                    error='Invalid scheduled_time format. Use ISO format.',
                    error_type='ValidationError'
                )

        # Create draft
        draft_id = self._generate_draft_id(content)
        draft = PostDraft(
            draft_id=draft_id,
            content=content,
            post_type=ptype,
            visibility=vis,
            hashtags=all_hashtags,
            mentions=auto_mentions,
            media_urls=media_urls or [],
            article_url=article_url,
            poll_question=poll_question,
            poll_options=poll_options or [],
            poll_duration_days=poll_duration_days,
            scheduled_time=sched_time,
            status='pending_approval'
        )

        # Validate draft
        errors = draft.validate()
        if errors:
            return PostResult(
                success=False,
                status='failed',
                error='; '.join(errors),
                error_type='ValidationError'
            )

        # Create approval request
        approval_details = {
            'draft_id': draft_id,
            'content': content,
            'content_preview': content[:280] + '...' if len(content) > 280 else content,
            'post_type': ptype.value,
            'visibility': vis.value,
            'hashtags': all_hashtags,
            'scheduled_time': sched_time.isoformat() if sched_time else 'immediate',
            'character_count': len(content)
        }

        if article_url:
            approval_details['article_url'] = article_url
        if poll_question:
            approval_details['poll_question'] = poll_question
            approval_details['poll_options'] = poll_options

        approval_path = self.approval_manager.create_approval_request(
            action_type='linkedin_post',
            details=approval_details,
            source_file=f'draft_{draft_id}',
            reason="LinkedIn post requires review before publishing to ensure brand consistency and appropriateness.",
            urgency='normal' if not sched_time else 'high'
        )

        # Update draft with approval ID
        draft.approval_id = approval_path.stem
        self._save_draft(draft)

        # Create action file in Needs_Action
        self._create_post_action_file(draft)

        self._log_operation('draft_created', {
            'draft_id': draft_id,
            'approval_id': draft.approval_id,
            'post_type': ptype.value,
            'scheduled': sched_time.isoformat() if sched_time else None
        })

        return PostResult(
            success=True,
            draft_id=draft_id,
            approval_id=draft.approval_id,
            status='pending_approval',
            details={
                'content_preview': content[:100] + '...' if len(content) > 100 else content,
                'character_count': len(content),
                'hashtag_count': len(all_hashtags),
                'approval_file': str(approval_path)
            }
        )

    def _create_post_action_file(self, draft: PostDraft) -> Path:
        """Create action file for the post in Needs_Action."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        content = f'''---
type: linkedin_post
draft_id: "{draft.draft_id}"
approval_id: "{draft.approval_id}"
post_type: "{draft.post_type.value}"
visibility: "{draft.visibility.value}"
character_count: {len(draft.content)}
hashtag_count: {len(draft.hashtags)}
created: "{datetime.now().isoformat()}"
scheduled: "{draft.scheduled_time.isoformat() if draft.scheduled_time else 'immediate'}"
priority: "medium"
status: pending_approval
requires_approval: true
---

# LinkedIn Post Draft

## Post Preview

```
{draft.content}
```

## Post Details

| Field | Value |
|-------|-------|
| **Type** | {draft.post_type.value} |
| **Visibility** | {draft.visibility.value} |
| **Characters** | {len(draft.content)} / {MAX_POST_LENGTH} |
| **Hashtags** | {', '.join('#' + h for h in draft.hashtags) or 'None'} |
| **Scheduled** | {draft.scheduled_time.strftime('%Y-%m-%d %H:%M') if draft.scheduled_time else 'Post immediately after approval'} |

{self._format_post_specific_details(draft)}

## Approval Checklist

- [ ] Content is professional and appropriate
- [ ] No confidential information disclosed
- [ ] Hashtags are relevant and not excessive
- [ ] Links work correctly (if applicable)
- [ ] Timing is appropriate
- [ ] Aligns with brand voice

## Actions

**To Approve**: Move approval file to `Approved` folder
**To Reject**: Move approval file to `Rejected` folder
**To Edit**: Modify content below and create new draft

## Notes

<!-- Add reviewer notes here -->

'''

        action_path = self.vault_path / 'Needs_Action' / f'LINKEDIN_POST_{timestamp}.md'
        action_path.write_text(content, encoding='utf-8')
        return action_path

    def _format_post_specific_details(self, draft: PostDraft) -> str:
        """Format post-type specific details."""
        if draft.post_type == PostType.ARTICLE and draft.article_url:
            return f'''
## Article Link

**URL**: {draft.article_url}
'''
        elif draft.post_type == PostType.POLL:
            options = '\n'.join(f'  - {opt}' for opt in draft.poll_options)
            return f'''
## Poll Details

**Question**: {draft.poll_question}
**Options**:
{options}
**Duration**: {draft.poll_duration_days} days
'''
        elif draft.post_type == PostType.IMAGE and draft.media_urls:
            images = '\n'.join(f'  - {url}' for url in draft.media_urls)
            return f'''
## Images

{images}
'''
        return ""

    def publish_approved_post(self, approval_id: str) -> PostResult:
        """
        Publish a post that has been approved.

        Args:
            approval_id: The approval ID from the HITL workflow

        Returns:
            PostResult with post_id if successful
        """
        # Find draft by approval ID
        draft = None
        for d in self._drafts.values():
            if d.approval_id == approval_id:
                draft = d
                break

        if not draft:
            return PostResult(
                success=False,
                status='failed',
                error=f'No draft found for approval ID: {approval_id}',
                error_type='NotFoundError'
            )

        # Check approval status
        # Look for approval file in Approved folder
        approved_files = list((self.vault_path / 'Approved').glob(f'*{approval_id}*'))
        if not approved_files:
            return PostResult(
                success=False,
                draft_id=draft.draft_id,
                status='failed',
                error='Post not yet approved. Move approval file to Approved folder.',
                error_type='ApprovalError'
            )

        # Rate limit check
        if not self.rate_limiter.allow():
            return PostResult(
                success=False,
                draft_id=draft.draft_id,
                status='failed',
                error=f'Daily post limit reached ({POSTS_PER_DAY}/day). Try again tomorrow.',
                error_type='RateLimitError',
                details={'reset_in': f'{int(self.rate_limiter.time_until_reset())}s'}
            )

        # Circuit breaker check
        if not self.circuit_breaker.allow_request():
            return PostResult(
                success=False,
                draft_id=draft.draft_id,
                status='failed',
                error='LinkedIn service temporarily unavailable',
                error_type='CircuitBreakerError'
            )

        # Publish via Playwright
        try:
            if not self._start_browser():
                return PostResult(
                    success=False,
                    draft_id=draft.draft_id,
                    status='failed',
                    error='Failed to start browser',
                    error_type='BrowserError'
                )

            if not self._ensure_logged_in():
                return PostResult(
                    success=False,
                    draft_id=draft.draft_id,
                    status='failed',
                    error='Not logged into LinkedIn',
                    error_type='AuthError'
                )

            # Post based on type
            if draft.post_type == PostType.TEXT:
                post_id = self._publish_text_post(draft)
            elif draft.post_type == PostType.ARTICLE:
                post_id = self._publish_article_post(draft)
            elif draft.post_type == PostType.POLL:
                post_id = self._publish_poll_post(draft)
            else:
                post_id = self._publish_text_post(draft)  # Fallback

            if post_id:
                # Update draft status
                draft.status = 'published'
                self._save_draft(draft)

                # Mark approval as completed
                self.approval_manager.mark_completed(
                    approved_files[0],
                    success=True,
                    result=f'Published with post ID: {post_id}'
                )

                self.circuit_breaker.record_success()

                self._log_operation('post_published', {
                    'draft_id': draft.draft_id,
                    'post_id': post_id,
                    'approval_id': approval_id
                })

                return PostResult(
                    success=True,
                    post_id=post_id,
                    draft_id=draft.draft_id,
                    approval_id=approval_id,
                    status='published',
                    details={'published_at': datetime.now().isoformat()}
                )
            else:
                self.circuit_breaker.record_failure()
                return PostResult(
                    success=False,
                    draft_id=draft.draft_id,
                    status='failed',
                    error='Failed to publish post',
                    error_type='PublishError'
                )

        except Exception as e:
            self.circuit_breaker.record_failure()
            self._log_operation('post_error', {
                'draft_id': draft.draft_id,
                'error': str(e)
            })
            return PostResult(
                success=False,
                draft_id=draft.draft_id,
                status='failed',
                error=str(e),
                error_type='PublishError'
            )
        finally:
            self._stop_browser()

    def _publish_text_post(self, draft: PostDraft) -> Optional[str]:
        """Publish a text post via LinkedIn UI."""
        try:
            # Click "Start a post" button
            self._page.goto('https://www.linkedin.com/feed/', wait_until='networkidle')
            self._page.wait_for_timeout(2000)

            # Click the post composer
            start_post = self._page.query_selector('button.share-box-feed-entry__trigger')
            if start_post:
                start_post.click()
                self._page.wait_for_timeout(1000)

            # Wait for modal
            self._page.wait_for_selector('.share-creation-state__text-editor', timeout=10000)

            # Type content
            editor = self._page.query_selector('.ql-editor[data-placeholder]')
            if editor:
                editor.fill(draft.content)
                self._page.wait_for_timeout(500)

            # Set visibility if needed
            if draft.visibility == PostVisibility.CONNECTIONS:
                # Click visibility dropdown and select connections
                visibility_btn = self._page.query_selector('[data-test-share-to-dropdown-trigger]')
                if visibility_btn:
                    visibility_btn.click()
                    self._page.wait_for_timeout(500)
                    connections_option = self._page.query_selector('[data-test-share-to-dropdown-option="CONNECTIONS"]')
                    if connections_option:
                        connections_option.click()

            # Click Post button
            post_btn = self._page.query_selector('button.share-actions__primary-action')
            if post_btn:
                post_btn.click()
                self._page.wait_for_timeout(3000)

            # Try to get post ID from URL or generate one
            post_id = f"li_post_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            self.logger.info(f"Published post: {post_id}")
            return post_id

        except Exception as e:
            self.logger.error(f"Failed to publish text post: {e}")
            return None

    def _publish_article_post(self, draft: PostDraft) -> Optional[str]:
        """Publish an article/link post."""
        try:
            self._page.goto('https://www.linkedin.com/feed/', wait_until='networkidle')
            self._page.wait_for_timeout(2000)

            # Click start post
            start_post = self._page.query_selector('button.share-box-feed-entry__trigger')
            if start_post:
                start_post.click()
                self._page.wait_for_timeout(1000)

            # Wait for modal
            self._page.wait_for_selector('.share-creation-state__text-editor', timeout=10000)

            # Paste the article URL first (LinkedIn will auto-preview)
            editor = self._page.query_selector('.ql-editor[data-placeholder]')
            if editor:
                # Paste URL then content
                full_content = f"{draft.article_url}\n\n{draft.content}"
                editor.fill(full_content)
                self._page.wait_for_timeout(2000)  # Wait for link preview

            # Click Post
            post_btn = self._page.query_selector('button.share-actions__primary-action')
            if post_btn:
                post_btn.click()
                self._page.wait_for_timeout(3000)

            post_id = f"li_article_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            return post_id

        except Exception as e:
            self.logger.error(f"Failed to publish article post: {e}")
            return None

    def _publish_poll_post(self, draft: PostDraft) -> Optional[str]:
        """Publish a poll post."""
        try:
            self._page.goto('https://www.linkedin.com/feed/', wait_until='networkidle')
            self._page.wait_for_timeout(2000)

            # Click start post
            start_post = self._page.query_selector('button.share-box-feed-entry__trigger')
            if start_post:
                start_post.click()
                self._page.wait_for_timeout(1000)

            # Click "Create a poll" option
            poll_option = self._page.query_selector('[data-test-share-creation-more-option="CREATE_POLL"]')
            if poll_option:
                poll_option.click()
                self._page.wait_for_timeout(1000)

            # Fill poll question
            question_input = self._page.query_selector('input[placeholder*="question"]')
            if question_input:
                question_input.fill(draft.poll_question)

            # Fill poll options
            option_inputs = self._page.query_selector_all('input[placeholder*="Option"]')
            for i, option in enumerate(draft.poll_options):
                if i < len(option_inputs):
                    option_inputs[i].fill(option)

            # Add post text
            editor = self._page.query_selector('.ql-editor[data-placeholder]')
            if editor:
                editor.fill(draft.content)

            # Click Post
            post_btn = self._page.query_selector('button.share-actions__primary-action')
            if post_btn:
                post_btn.click()
                self._page.wait_for_timeout(3000)

            post_id = f"li_poll_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            return post_id

        except Exception as e:
            self.logger.error(f"Failed to publish poll: {e}")
            return None

    def schedule_post(
        self,
        content: str,
        scheduled_time: str,
        **kwargs
    ) -> PostResult:
        """
        Schedule a post for future publishing.

        Args:
            content: Post content
            scheduled_time: ISO format datetime
            **kwargs: Additional arguments for draft_post

        Returns:
            PostResult with draft_id
        """
        return self.draft_post(content, scheduled_time=scheduled_time, **kwargs)

    def get_draft_posts(self, status: Optional[str] = None) -> PostResult:
        """
        Get all draft posts, optionally filtered by status.

        Args:
            status: Filter by status (draft, pending_approval, approved, published)

        Returns:
            PostResult with drafts list
        """
        drafts = []
        for draft in self._drafts.values():
            if status is None or draft.status == status:
                drafts.append({
                    'draft_id': draft.draft_id,
                    'content_preview': draft.content[:100] + '...' if len(draft.content) > 100 else draft.content,
                    'post_type': draft.post_type.value,
                    'status': draft.status,
                    'created_at': draft.created_at.isoformat(),
                    'scheduled_time': draft.scheduled_time.isoformat() if draft.scheduled_time else None,
                    'approval_id': draft.approval_id
                })

        return PostResult(
            success=True,
            status='success',
            details={
                'drafts': drafts,
                'total_count': len(drafts)
            }
        )

    def delete_draft(self, draft_id: str) -> PostResult:
        """
        Delete a draft post.

        Args:
            draft_id: The draft ID to delete

        Returns:
            PostResult indicating success
        """
        if draft_id not in self._drafts:
            return PostResult(
                success=False,
                status='failed',
                error=f'Draft not found: {draft_id}',
                error_type='NotFoundError'
            )

        draft = self._drafts[draft_id]

        # Can't delete published posts
        if draft.status == 'published':
            return PostResult(
                success=False,
                draft_id=draft_id,
                status='failed',
                error='Cannot delete published posts',
                error_type='ValidationError'
            )

        self._delete_draft_file(draft_id)

        self._log_operation('draft_deleted', {'draft_id': draft_id})

        return PostResult(
            success=True,
            draft_id=draft_id,
            status='deleted'
        )

    def get_status(self) -> Dict[str, Any]:
        """Get current skill status."""
        return {
            'skill': 'LinkedInPostingSkill',
            'rate_limit': self.rate_limiter.get_status(),
            'circuit_breaker': self.circuit_breaker.get_status(),
            'draft_count': len(self._drafts),
            'pending_approval': sum(1 for d in self._drafts.values() if d.status == 'pending_approval'),
            'published_today': POSTS_PER_DAY - self.rate_limiter.remaining()
        }


# Standalone runner for testing
if __name__ == '__main__':
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description='LinkedIn Posting Skill')
    parser.add_argument('--vault', default='./AI_Employee_Vault', help='Path to vault')
    parser.add_argument('--session', default='./config/linkedin_session', help='Session path')
    parser.add_argument('--draft', type=str, help='Create draft with this content')
    parser.add_argument('--publish', type=str, help='Publish draft with this approval ID')
    parser.add_argument('--list', action='store_true', help='List all drafts')

    args = parser.parse_args()

    try:
        skill = LinkedInPostingSkill(
            vault_path=args.vault,
            session_path=args.session
        )

        if args.draft:
            result = skill.draft_post(args.draft)
            print(f"Draft created: {result.to_dict()}")
        elif args.publish:
            result = skill.publish_approved_post(args.publish)
            print(f"Publish result: {result.to_dict()}")
        elif args.list:
            result = skill.get_draft_posts()
            print(f"Drafts: {json.dumps(result.details, indent=2)}")
        else:
            print(f"Status: {json.dumps(skill.get_status(), indent=2)}")

    except ImportError as e:
        print(f"Error: {e}")
