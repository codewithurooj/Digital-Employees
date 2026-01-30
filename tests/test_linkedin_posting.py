"""
Tests for LinkedIn Posting Skill

Run with: pytest tests/test_linkedin_posting.py -v
"""

import pytest
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Check if playwright is installed, skip tests if not
pytest.importorskip("playwright", reason="Playwright not installed")

from src.skills.linkedin_posting import (
    LinkedInPostingSkill,
    PostDraft,
    PostResult,
    PostVisibility,
    PostType,
    MAX_POST_LENGTH,
    MAX_HASHTAGS,
    POSTS_PER_DAY
)


class TestPostDraft:
    """Test PostDraft dataclass."""

    def test_create_basic_draft(self):
        """Can create basic draft."""
        draft = PostDraft(
            draft_id="test_123",
            content="Hello LinkedIn!"
        )
        assert draft.draft_id == "test_123"
        assert draft.content == "Hello LinkedIn!"
        assert draft.post_type == PostType.TEXT
        assert draft.visibility == PostVisibility.PUBLIC

    def test_validate_empty_content(self):
        """Validation fails for empty content."""
        draft = PostDraft(draft_id="test", content="")
        errors = draft.validate()
        assert any("empty" in e.lower() for e in errors)

    def test_validate_content_too_long(self):
        """Validation fails for content exceeding limit."""
        draft = PostDraft(
            draft_id="test",
            content="x" * (MAX_POST_LENGTH + 100)
        )
        errors = draft.validate()
        assert any("exceeds" in e.lower() for e in errors)

    def test_validate_too_many_hashtags(self):
        """Validation fails for too many hashtags."""
        draft = PostDraft(
            draft_id="test",
            content="Test post",
            hashtags=["tag" + str(i) for i in range(MAX_HASHTAGS + 5)]
        )
        errors = draft.validate()
        assert any("hashtag" in e.lower() for e in errors)

    def test_validate_poll_requires_question(self):
        """Poll post requires question."""
        draft = PostDraft(
            draft_id="test",
            content="Vote now!",
            post_type=PostType.POLL,
            poll_options=["Option 1", "Option 2"]
        )
        errors = draft.validate()
        assert any("question" in e.lower() for e in errors)

    def test_validate_poll_requires_options(self):
        """Poll post requires at least 2 options."""
        draft = PostDraft(
            draft_id="test",
            content="Vote now!",
            post_type=PostType.POLL,
            poll_question="What do you think?",
            poll_options=["Only one"]
        )
        errors = draft.validate()
        assert any("option" in e.lower() for e in errors)

    def test_validate_article_requires_url(self):
        """Article post requires URL."""
        draft = PostDraft(
            draft_id="test",
            content="Check this out",
            post_type=PostType.ARTICLE
        )
        errors = draft.validate()
        assert any("url" in e.lower() for e in errors)

    def test_validate_valid_draft(self):
        """Valid draft has no errors."""
        draft = PostDraft(
            draft_id="test",
            content="This is a valid post! #linkedin #test",
            hashtags=["linkedin", "test"]
        )
        errors = draft.validate()
        assert len(errors) == 0

    def test_to_dict(self):
        """Draft converts to dictionary."""
        draft = PostDraft(
            draft_id="test_123",
            content="Hello World",
            hashtags=["test"]
        )
        d = draft.to_dict()
        assert d['draft_id'] == "test_123"
        assert d['content'] == "Hello World"
        assert d['hashtags'] == ["test"]
        assert d['post_type'] == "text"


class TestPostResult:
    """Test PostResult dataclass."""

    def test_success_result(self):
        """Can create success result."""
        result = PostResult(
            success=True,
            post_id="post_123",
            status="published"
        )
        assert result.success is True
        assert result.post_id == "post_123"

    def test_failure_result(self):
        """Can create failure result."""
        result = PostResult(
            success=False,
            error="Rate limit exceeded",
            error_type="RateLimitError"
        )
        assert result.success is False
        assert result.error == "Rate limit exceeded"

    def test_to_dict(self):
        """Result converts to dictionary."""
        result = PostResult(
            success=True,
            post_id="123",
            draft_id="draft_456",
            status="published"
        )
        d = result.to_dict()
        assert d['success'] is True
        assert d['post_id'] == "123"
        assert d['draft_id'] == "draft_456"


class TestLinkedInPostingSkillInit:
    """Test skill initialization."""

    @pytest.fixture
    def temp_vault(self, tmp_path):
        """Create temporary vault."""
        vault = tmp_path / "AI_Employee_Vault"
        folders = [
            "Inbox", "Needs_Action", "Plans", "Pending_Approval",
            "Approved", "Rejected", "Done", "Logs"
        ]
        for folder in folders:
            (vault / folder).mkdir(parents=True, exist_ok=True)
        return vault

    def test_init_creates_drafts_folder(self, temp_vault):
        """Initialization creates drafts folder."""
        skill = LinkedInPostingSkill(vault_path=str(temp_vault))
        assert (temp_vault / "Plans" / "linkedin_drafts").exists()

    def test_init_sets_rate_limiter(self, temp_vault):
        """Initialization sets rate limiter."""
        skill = LinkedInPostingSkill(vault_path=str(temp_vault))
        assert skill.rate_limiter.max_calls == POSTS_PER_DAY

    def test_init_sets_circuit_breaker(self, temp_vault):
        """Initialization sets circuit breaker."""
        skill = LinkedInPostingSkill(vault_path=str(temp_vault))
        assert skill.circuit_breaker.name == 'linkedin'


class TestDraftPost:
    """Test draft_post method."""

    @pytest.fixture
    def skill(self, tmp_path):
        """Create skill for testing."""
        vault = tmp_path / "AI_Employee_Vault"
        for folder in ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Rejected", "Done", "Logs", "Inbox"]:
            (vault / folder).mkdir(parents=True, exist_ok=True)
        return LinkedInPostingSkill(vault_path=str(vault))

    def test_draft_creates_draft(self, skill):
        """Draft post creates a draft."""
        result = skill.draft_post("Hello LinkedIn! #test")

        assert result.success is True
        assert result.draft_id is not None
        assert result.approval_id is not None
        assert result.status == 'pending_approval'

    def test_draft_extracts_hashtags(self, skill):
        """Draft extracts hashtags from content."""
        result = skill.draft_post("Check out #AI and #MachineLearning trends")

        draft = skill._drafts[result.draft_id]
        assert 'AI' in draft.hashtags
        assert 'MachineLearning' in draft.hashtags

    def test_draft_saves_to_disk(self, skill):
        """Draft is saved to disk."""
        result = skill.draft_post("Test post")

        draft_file = skill.drafts_path / f'{result.draft_id}.json'
        assert draft_file.exists()

    def test_draft_creates_approval_request(self, skill):
        """Draft creates approval request."""
        result = skill.draft_post("Need approval for this")

        pending_files = list(skill.vault_path.glob('Pending_Approval/*.md'))
        assert len(pending_files) >= 1

    def test_draft_creates_action_file(self, skill):
        """Draft creates action file in Needs_Action."""
        result = skill.draft_post("Action needed")

        action_files = list(skill.vault_path.glob('Needs_Action/LINKEDIN_POST_*.md'))
        assert len(action_files) >= 1

    def test_draft_validates_content(self, skill):
        """Draft validates content length."""
        result = skill.draft_post("x" * (MAX_POST_LENGTH + 100))

        assert result.success is False
        assert 'exceeds' in result.error.lower()

    def test_draft_with_visibility(self, skill):
        """Draft respects visibility setting."""
        result = skill.draft_post("Connections only", visibility="connections")

        assert result.success is True
        draft = skill._drafts[result.draft_id]
        assert draft.visibility == PostVisibility.CONNECTIONS

    def test_draft_invalid_visibility(self, skill):
        """Draft fails with invalid visibility."""
        result = skill.draft_post("Test", visibility="invalid")

        assert result.success is False
        assert 'ValidationError' in result.error_type

    def test_draft_with_schedule(self, skill):
        """Draft with scheduled time."""
        future_time = (datetime.now() + timedelta(days=1)).isoformat()
        result = skill.draft_post("Scheduled post", scheduled_time=future_time)

        assert result.success is True
        draft = skill._drafts[result.draft_id]
        assert draft.scheduled_time is not None

    def test_draft_past_schedule_fails(self, skill):
        """Draft with past scheduled time fails."""
        past_time = (datetime.now() - timedelta(days=1)).isoformat()
        result = skill.draft_post("Past post", scheduled_time=past_time)

        assert result.success is False
        assert 'future' in result.error.lower()


class TestGetDraftPosts:
    """Test get_draft_posts method."""

    @pytest.fixture
    def skill_with_drafts(self, tmp_path):
        """Create skill with some drafts."""
        vault = tmp_path / "AI_Employee_Vault"
        for folder in ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Rejected", "Done", "Logs", "Inbox"]:
            (vault / folder).mkdir(parents=True, exist_ok=True)

        skill = LinkedInPostingSkill(vault_path=str(vault))

        # Create some drafts
        skill.draft_post("Draft 1")
        skill.draft_post("Draft 2")

        return skill

    def test_get_all_drafts(self, skill_with_drafts):
        """Get all drafts."""
        result = skill_with_drafts.get_draft_posts()

        assert result.success is True
        assert result.details['total_count'] == 2

    def test_get_drafts_by_status(self, skill_with_drafts):
        """Filter drafts by status."""
        result = skill_with_drafts.get_draft_posts(status='pending_approval')

        assert result.success is True
        assert result.details['total_count'] == 2


class TestDeleteDraft:
    """Test delete_draft method."""

    @pytest.fixture
    def skill(self, tmp_path):
        """Create skill for testing."""
        vault = tmp_path / "AI_Employee_Vault"
        for folder in ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Rejected", "Done", "Logs", "Inbox"]:
            (vault / folder).mkdir(parents=True, exist_ok=True)
        return LinkedInPostingSkill(vault_path=str(vault))

    def test_delete_existing_draft(self, skill):
        """Can delete existing draft."""
        create_result = skill.draft_post("To be deleted")
        delete_result = skill.delete_draft(create_result.draft_id)

        assert delete_result.success is True
        assert create_result.draft_id not in skill._drafts

    def test_delete_nonexistent_draft(self, skill):
        """Deleting nonexistent draft fails."""
        result = skill.delete_draft("nonexistent_id")

        assert result.success is False
        assert 'NotFoundError' in result.error_type

    def test_delete_removes_file(self, skill):
        """Delete removes draft file."""
        create_result = skill.draft_post("File to delete")
        draft_file = skill.drafts_path / f'{create_result.draft_id}.json'

        assert draft_file.exists()
        skill.delete_draft(create_result.draft_id)
        assert not draft_file.exists()


class TestGetStatus:
    """Test get_status method."""

    @pytest.fixture
    def skill(self, tmp_path):
        """Create skill for testing."""
        vault = tmp_path / "AI_Employee_Vault"
        for folder in ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Rejected", "Done", "Logs", "Inbox"]:
            (vault / folder).mkdir(parents=True, exist_ok=True)
        return LinkedInPostingSkill(vault_path=str(vault))

    def test_status_includes_skill_name(self, skill):
        """Status includes skill name."""
        status = skill.get_status()
        assert status['skill'] == 'LinkedInPostingSkill'

    def test_status_includes_rate_limit(self, skill):
        """Status includes rate limit info."""
        status = skill.get_status()
        assert 'rate_limit' in status

    def test_status_includes_circuit_breaker(self, skill):
        """Status includes circuit breaker info."""
        status = skill.get_status()
        assert 'circuit_breaker' in status

    def test_status_includes_draft_count(self, skill):
        """Status includes draft count."""
        skill.draft_post("Test draft")
        status = skill.get_status()

        assert status['draft_count'] == 1
        assert status['pending_approval'] == 1


class TestHelperMethods:
    """Test helper methods."""

    @pytest.fixture
    def skill(self, tmp_path):
        """Create skill for testing."""
        vault = tmp_path / "AI_Employee_Vault"
        for folder in ["Needs_Action", "Plans", "Pending_Approval", "Approved", "Rejected", "Done", "Logs", "Inbox"]:
            (vault / folder).mkdir(parents=True, exist_ok=True)
        return LinkedInPostingSkill(vault_path=str(vault))

    def test_extract_hashtags(self, skill):
        """Extracts hashtags from content."""
        hashtags = skill._extract_hashtags("Check out #AI and #tech trends #2024")
        assert 'AI' in hashtags
        assert 'tech' in hashtags
        assert '2024' in hashtags

    def test_extract_mentions(self, skill):
        """Extracts mentions from content."""
        mentions = skill._extract_mentions("Thanks @john and @company for this")
        assert 'john' in mentions
        assert 'company' in mentions

    def test_generate_draft_id_unique(self, skill):
        """Generated draft IDs are unique."""
        id1 = skill._generate_draft_id("Content 1")
        id2 = skill._generate_draft_id("Content 2")
        assert id1 != id2

    def test_generate_draft_id_format(self, skill):
        """Draft ID has expected format."""
        draft_id = skill._generate_draft_id("Test content")
        assert draft_id.startswith("draft_")
