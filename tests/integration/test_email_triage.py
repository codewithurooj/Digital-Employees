"""Integration tests for email triage flow (T048)."""

import pytest
from datetime import datetime


class TestEmailTriageFlow:
    """Tests for the email triage skill."""

    def test_triage_categorizes_urgent_email(self, tmp_path):
        """Urgent keywords should produce 'urgent' priority."""
        from src.skills.email_triage import EmailTriageSkill

        skill = EmailTriageSkill(vault_path=str(tmp_path))
        result = skill.categorize_email({
            "from": "client@example.com",
            "subject": "URGENT: Server is down",
            "body": "Please help immediately, production is down!",
            "date": datetime.now().isoformat(),
        })
        assert result["priority"] == "urgent"

    def test_triage_categorizes_normal_email(self, tmp_path):
        from src.skills.email_triage import EmailTriageSkill

        skill = EmailTriageSkill(vault_path=str(tmp_path))
        result = skill.categorize_email({
            "from": "vendor@example.com",
            "subject": "Monthly Invoice #1234",
            "body": "Please find attached your monthly invoice.",
            "date": datetime.now().isoformat(),
        })
        assert result["priority"] == "normal"

    def test_triage_categorizes_low_priority_email(self, tmp_path):
        from src.skills.email_triage import EmailTriageSkill

        skill = EmailTriageSkill(vault_path=str(tmp_path))
        result = skill.categorize_email({
            "from": "newsletter@company.com",
            "subject": "Weekly Newsletter",
            "body": "Here are this week's updates and news.",
            "date": datetime.now().isoformat(),
        })
        assert result["priority"] == "low"

    def test_triage_creates_draft_in_vault(self, tmp_path):
        from src.skills.email_triage import EmailTriageSkill

        skill = EmailTriageSkill(vault_path=str(tmp_path))
        result = skill.triage_email({
            "from": "client@example.com",
            "subject": "Question about project",
            "body": "When will the project be delivered?",
            "date": datetime.now().isoformat(),
            "message_id": "msg_123",
        })
        assert result["success"] is True
        draft_files = list((tmp_path / "Pending_Approval" / "email").glob("*.md"))
        assert len(draft_files) >= 1

    def test_triage_creates_summary(self, tmp_path):
        from src.skills.email_triage import EmailTriageSkill

        skill = EmailTriageSkill(vault_path=str(tmp_path))
        emails = [
            {"from": "a@b.com", "subject": "Meeting", "body": "Let's meet",
             "date": datetime.now().isoformat(), "message_id": "m1"},
            {"from": "c@d.com", "subject": "URGENT: Help", "body": "Need help now",
             "date": datetime.now().isoformat(), "message_id": "m2"},
        ]
        summary = skill.generate_summary(emails)
        assert "Urgent" in summary or "urgent" in summary.lower()
        assert "Meeting" in summary

    def test_triage_logs_action(self, tmp_path):
        from src.skills.email_triage import EmailTriageSkill

        skill = EmailTriageSkill(vault_path=str(tmp_path))
        skill.triage_email({
            "from": "test@test.com",
            "subject": "Test",
            "body": "Test body",
            "date": datetime.now().isoformat(),
            "message_id": "msg_test",
        })
        log_files = list((tmp_path / "Logs").glob("*.jsonl"))
        assert len(log_files) >= 1
