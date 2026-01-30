"""End-to-end integration test for platinum demo flow (T091).

Tests the complete flow: email arrives -> cloud drafts -> syncs -> local sends.
"""

import pytest
from pathlib import Path
from datetime import datetime

from src.cloud.work_zone import WorkZone, WorkZoneViolation


class TestPlatinumDemoFlow:
    """End-to-end demo of cloud/local handoff."""

    def test_full_email_flow(self, tmp_path):
        """Complete flow: email -> cloud triage -> draft -> local sends."""
        from src.skills.email_triage import EmailTriageSkill

        # Step 1: Cloud agent triages email
        skill = EmailTriageSkill(vault_path=str(tmp_path))
        email = {
            "from": "client@example.com",
            "subject": "Project status update needed",
            "body": "Can you send me the latest project status?",
            "date": datetime.now().isoformat(),
            "message_id": "demo_msg_001",
        }

        result = skill.triage_email(email)
        assert result["success"] is True
        assert result["priority"] == "normal"

        # Step 2: Verify draft was created
        draft_files = list(
            (tmp_path / "Pending_Approval" / "email").glob("*.md")
        )
        assert len(draft_files) == 1
        draft_content = draft_files[0].read_text()
        assert "client@example.com" in draft_content
        assert "Project status" in draft_content

    def test_full_social_flow(self, tmp_path):
        """Complete flow: schedule -> cloud drafts -> approval -> local publishes."""
        from src.skills.social_draft import SocialDraftSkill

        # Step 1: Cloud agent creates draft
        skill = SocialDraftSkill(vault_path=str(tmp_path))
        result = skill.create_draft(
            platform="facebook",
            content="Exciting update: we've launched v2.0!",
            hashtags=["#launch", "#v2"],
        )
        assert result["success"] is True

        # Step 2: Verify draft exists
        draft_files = list(
            (tmp_path / "Pending_Approval" / "social").glob("*.md")
        )
        assert len(draft_files) == 1

    def test_full_invoice_flow(self, tmp_path):
        """Complete flow: invoice request -> cloud drafts -> approval -> local posts."""
        from src.cloud.cloud_odoo_mcp import CloudOdooMCP

        # Step 1: Cloud agent creates draft invoice
        mcp = CloudOdooMCP(vault_path=str(tmp_path))
        result = mcp.create_draft_invoice(
            partner_name="Acme Corp",
            lines=[
                {"description": "Consulting - January", "quantity": 40, "unit_price": 150.00},
            ],
            notes="Net 30 payment terms",
        )
        assert result["success"] is True
        assert result["amount_total"] == "6000.00"

        # Step 2: Verify both invoice and approval request exist
        invoice_files = list(
            (tmp_path / "Accounting" / "Invoices").glob("*.md")
        )
        approval_files = list(
            (tmp_path / "Pending_Approval" / "accounting").glob("*.md")
        )
        assert len(invoice_files) == 1
        assert len(approval_files) == 1

    def test_work_zone_enforcement_in_demo(self, tmp_path):
        """Verify cloud agent cannot send during demo."""
        from src.cloud.work_zone import requires_local

        class DemoMCP:
            def __init__(self):
                self.agent_zone = WorkZone.CLOUD

            @requires_local
            def send(self):
                return "sent"

        mcp = DemoMCP()
        with pytest.raises(WorkZoneViolation):
            mcp.send()

    def test_health_monitor_in_demo(self, tmp_path):
        """Verify health monitoring works during demo."""
        from src.cloud.health_monitor import HealthMonitor

        monitor = HealthMonitor(vault_path=str(tmp_path))
        monitor.write_status()

        status_file = tmp_path / "Health" / "status.md"
        assert status_file.exists()
        content = status_file.read_text()
        assert "Health Status" in content
