"""Integration tests for social media draft flow (T055)."""

import pytest
from pathlib import Path
from datetime import datetime, timedelta


class TestSocialDraftFlow:
    """Tests for the social draft skill."""

    def test_draft_creates_file_in_vault(self, tmp_path):
        from src.skills.social_draft import SocialDraftSkill

        skill = SocialDraftSkill(vault_path=str(tmp_path))
        result = skill.create_draft(
            platform="facebook",
            content="Exciting product launch today!",
            hashtags=["#launch", "#newproduct"],
        )
        assert result["success"] is True
        draft_files = list((tmp_path / "Pending_Approval" / "social").glob("*.md"))
        assert len(draft_files) == 1

    def test_draft_validates_platform(self, tmp_path):
        from src.skills.social_draft import SocialDraftSkill

        skill = SocialDraftSkill(vault_path=str(tmp_path))
        result = skill.create_draft(
            platform="tiktok",
            content="Test",
        )
        assert result["success"] is False
        assert "platform" in result.get("error", "").lower()

    def test_draft_validates_content_length_twitter(self, tmp_path):
        from src.skills.social_draft import SocialDraftSkill

        skill = SocialDraftSkill(vault_path=str(tmp_path))
        result = skill.create_draft(
            platform="twitter",
            content="x" * 300,  # over 280 char limit
        )
        assert result["success"] is False

    def test_scheduling_check_upcoming(self, tmp_path):
        from src.skills.social_draft import SocialDraftSkill

        skill = SocialDraftSkill(vault_path=str(tmp_path))
        skill.create_draft(
            platform="facebook",
            content="Scheduled post!",
            scheduled_for=datetime.now() + timedelta(minutes=30),
        )
        upcoming = skill.get_upcoming_posts(within_minutes=60)
        assert len(upcoming) >= 1

    def test_draft_includes_hashtags(self, tmp_path):
        from src.skills.social_draft import SocialDraftSkill

        skill = SocialDraftSkill(vault_path=str(tmp_path))
        result = skill.create_draft(
            platform="instagram",
            content="Beautiful sunset",
            hashtags=["#sunset", "#photography"],
        )
        assert result["success"] is True
        draft_path = Path(result["draft_path"])
        content = draft_path.read_text()
        assert "#sunset" in content

    def test_draft_logs_action(self, tmp_path):
        from src.skills.social_draft import SocialDraftSkill

        skill = SocialDraftSkill(vault_path=str(tmp_path))
        skill.create_draft(platform="facebook", content="Test post")
        log_files = list((tmp_path / "Logs").glob("*.jsonl"))
        assert len(log_files) >= 1
