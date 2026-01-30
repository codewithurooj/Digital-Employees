"""
Integration tests for cloud -> local handoff flow (T040).

Validates the end-to-end work-zone handoff:
- Cloud agent can create drafts (allowed)
- Cloud agent is blocked from sending (requires local)
- Local agent can send (allowed)
- Audit logging on violation if available
- Full workflow: cloud drafts -> approval -> local sends
"""

import pytest

from src.cloud.work_zone import (
    WorkZone,
    WorkZoneViolation,
    requires_local,
)


# ---------------------------------------------------------------------------
# Simulated MCP server for integration testing
# ---------------------------------------------------------------------------

class SimulatedEmailMCP:
    """
    Simulated Email MCP that mirrors the real EmailMCPServer's
    work-zone integration without requiring Gmail API.
    """

    def __init__(self, agent_zone=None):
        self.agent_zone = agent_zone
        self.drafts = {}
        self.sent = []
        self.audit_events = []
        self._next_draft_id = 1

    def audit_log(self, event_type, details):
        """Audit log for tracking violations."""
        self.audit_events.append({"event_type": event_type, "details": details})

    def draft_email(self, to, subject, body):
        """Draft an email (allowed for both zones)."""
        draft_id = f"draft_{self._next_draft_id}"
        self._next_draft_id += 1
        self.drafts[draft_id] = {
            "to": to,
            "subject": subject,
            "body": body,
            "status": "draft",
        }
        return {"success": True, "draft_id": draft_id}

    @requires_local
    def send_email(self, draft_id, approval_id):
        """Send an email (local-only)."""
        if draft_id not in self.drafts:
            return {"success": False, "error": "Draft not found"}

        draft = self.drafts.pop(draft_id)
        draft["status"] = "sent"
        draft["approval_id"] = approval_id
        self.sent.append(draft)
        return {"success": True, "message_id": f"msg_{len(self.sent)}"}

    @requires_local
    def reply_email(self, message_id, body, approval_id):
        """Reply to an email (local-only)."""
        self.sent.append({
            "reply_to": message_id,
            "body": body,
            "approval_id": approval_id,
            "status": "sent",
        })
        return {"success": True}

    @requires_local
    def forward_email(self, message_id, to, approval_id):
        """Forward an email (local-only)."""
        self.sent.append({
            "forward_from": message_id,
            "to": to,
            "approval_id": approval_id,
            "status": "sent",
        })
        return {"success": True}


class SimulatedSocialMCP:
    """
    Simulated Social MCP that mirrors the real SocialMCP's
    work-zone integration without requiring social API clients.
    """

    def __init__(self, agent_zone=None):
        self.agent_zone = agent_zone
        self.drafts = {}
        self.published = []
        self.audit_events = []
        self._next_draft_id = 1

    def audit_log(self, event_type, details):
        self.audit_events.append({"event_type": event_type, "details": details})

    def draft_post(self, platform, content):
        """Draft a social post (allowed for both zones)."""
        draft_id = f"social_{self._next_draft_id}"
        self._next_draft_id += 1
        self.drafts[draft_id] = {
            "platform": platform,
            "content": content,
            "status": "draft",
        }
        return {"success": True, "draft_id": draft_id}

    @requires_local
    def publish_post(self, draft_id, approval_id):
        """Publish a post (local-only)."""
        if draft_id not in self.drafts:
            return {"success": False, "error": "Draft not found"}

        draft = self.drafts.pop(draft_id)
        draft["status"] = "published"
        draft["approval_id"] = approval_id
        self.published.append(draft)
        return {"success": True, "post_id": f"post_{len(self.published)}"}


# ---------------------------------------------------------------------------
# Cloud agent drafting tests
# ---------------------------------------------------------------------------

class TestCloudAgentDrafting:
    """Cloud agent should be able to create drafts."""

    def test_cloud_can_draft_email(self):
        mcp = SimulatedEmailMCP(agent_zone=WorkZone.CLOUD)
        result = mcp.draft_email(
            to=["client@example.com"],
            subject="Invoice",
            body="Please find attached.",
        )
        assert result["success"] is True
        assert "draft_id" in result

    def test_cloud_can_draft_social_post(self):
        mcp = SimulatedSocialMCP(agent_zone=WorkZone.CLOUD)
        result = mcp.draft_post(platform="facebook", content="Hello world!")
        assert result["success"] is True
        assert "draft_id" in result


# ---------------------------------------------------------------------------
# Cloud agent blocked from sending tests
# ---------------------------------------------------------------------------

class TestCloudAgentBlocked:
    """Cloud agent must be blocked from send/publish operations."""

    def test_cloud_blocked_from_send_email(self):
        mcp = SimulatedEmailMCP(agent_zone=WorkZone.CLOUD)

        # First draft (allowed)
        draft_result = mcp.draft_email(
            to=["client@example.com"],
            subject="Test",
            body="Body",
        )
        draft_id = draft_result["draft_id"]

        # Attempt to send (blocked)
        with pytest.raises(WorkZoneViolation) as exc_info:
            mcp.send_email(draft_id=draft_id, approval_id="appr_001")

        assert exc_info.value.action == "send_email"
        assert exc_info.value.zone == "cloud"
        assert exc_info.value.required == "local"

        # Draft should still exist (not consumed)
        assert draft_id in mcp.drafts

    def test_cloud_blocked_from_reply_email(self):
        mcp = SimulatedEmailMCP(agent_zone=WorkZone.CLOUD)

        with pytest.raises(WorkZoneViolation):
            mcp.reply_email(
                message_id="msg_123",
                body="Reply body",
                approval_id="appr_002",
            )

    def test_cloud_blocked_from_forward_email(self):
        mcp = SimulatedEmailMCP(agent_zone=WorkZone.CLOUD)

        with pytest.raises(WorkZoneViolation):
            mcp.forward_email(
                message_id="msg_123",
                to=["other@example.com"],
                approval_id="appr_003",
            )

    def test_cloud_blocked_from_publish_post(self):
        mcp = SimulatedSocialMCP(agent_zone=WorkZone.CLOUD)

        draft_result = mcp.draft_post(platform="twitter", content="Hello!")
        draft_id = draft_result["draft_id"]

        with pytest.raises(WorkZoneViolation) as exc_info:
            mcp.publish_post(draft_id=draft_id, approval_id="appr_004")

        assert exc_info.value.action == "publish_post"
        assert draft_id in mcp.drafts  # Draft not consumed


# ---------------------------------------------------------------------------
# Local agent can send tests
# ---------------------------------------------------------------------------

class TestLocalAgentSend:
    """Local agent must be able to execute send/publish operations."""

    def test_local_can_send_email(self):
        mcp = SimulatedEmailMCP(agent_zone=WorkZone.LOCAL)

        draft_result = mcp.draft_email(
            to=["client@example.com"],
            subject="Invoice",
            body="Attached.",
        )
        draft_id = draft_result["draft_id"]

        result = mcp.send_email(draft_id=draft_id, approval_id="appr_100")
        assert result["success"] is True
        assert "message_id" in result
        assert len(mcp.sent) == 1

    def test_local_can_reply_email(self):
        mcp = SimulatedEmailMCP(agent_zone=WorkZone.LOCAL)
        result = mcp.reply_email(
            message_id="msg_123",
            body="Thanks!",
            approval_id="appr_101",
        )
        assert result["success"] is True

    def test_local_can_forward_email(self):
        mcp = SimulatedEmailMCP(agent_zone=WorkZone.LOCAL)
        result = mcp.forward_email(
            message_id="msg_123",
            to=["other@example.com"],
            approval_id="appr_102",
        )
        assert result["success"] is True

    def test_local_can_publish_post(self):
        mcp = SimulatedSocialMCP(agent_zone=WorkZone.LOCAL)

        draft_result = mcp.draft_post(platform="facebook", content="Update!")
        draft_id = draft_result["draft_id"]

        result = mcp.publish_post(draft_id=draft_id, approval_id="appr_103")
        assert result["success"] is True
        assert len(mcp.published) == 1


# ---------------------------------------------------------------------------
# Audit logging on violation tests
# ---------------------------------------------------------------------------

class TestAuditLoggingOnViolation:
    """Audit log must be called when a violation occurs, if available."""

    def test_audit_log_called_on_email_violation(self):
        mcp = SimulatedEmailMCP(agent_zone=WorkZone.CLOUD)

        with pytest.raises(WorkZoneViolation):
            mcp.send_email(draft_id="draft_1", approval_id="appr_200")

        assert len(mcp.audit_events) == 1
        event = mcp.audit_events[0]
        assert event["event_type"] == "work_zone_violation"
        assert event["details"]["action"] == "send_email"

    def test_audit_log_called_on_social_violation(self):
        mcp = SimulatedSocialMCP(agent_zone=WorkZone.CLOUD)

        with pytest.raises(WorkZoneViolation):
            mcp.publish_post(draft_id="social_1", approval_id="appr_201")

        assert len(mcp.audit_events) == 1
        event = mcp.audit_events[0]
        assert event["event_type"] == "work_zone_violation"
        assert event["details"]["action"] == "publish_post"

    def test_no_audit_event_on_successful_local_send(self):
        mcp = SimulatedEmailMCP(agent_zone=WorkZone.LOCAL)
        mcp.draft_email(to=["a@b.com"], subject="S", body="B")
        mcp.send_email(draft_id="draft_1", approval_id="appr_202")

        assert len(mcp.audit_events) == 0


# ---------------------------------------------------------------------------
# Full workflow: cloud drafts -> approval -> local sends
# ---------------------------------------------------------------------------

class TestFullHandoffWorkflow:
    """End-to-end handoff: cloud drafts, then local agent sends."""

    def test_email_handoff_workflow(self):
        """Cloud drafts email -> local sends after approval."""
        # Step 1: Cloud agent drafts
        cloud_mcp = SimulatedEmailMCP(agent_zone=WorkZone.CLOUD)
        draft_result = cloud_mcp.draft_email(
            to=["client@example.com"],
            subject="Monthly Report",
            body="Please review the attached report.",
        )
        assert draft_result["success"] is True
        draft_id = draft_result["draft_id"]

        # Step 2: Cloud agent attempts send (should fail)
        with pytest.raises(WorkZoneViolation):
            cloud_mcp.send_email(draft_id=draft_id, approval_id="appr_300")

        # Step 3: Local agent picks up the draft and sends
        local_mcp = SimulatedEmailMCP(agent_zone=WorkZone.LOCAL)
        # Simulate transferring draft state
        local_mcp.drafts = cloud_mcp.drafts.copy()

        result = local_mcp.send_email(draft_id=draft_id, approval_id="appr_300")
        assert result["success"] is True
        assert len(local_mcp.sent) == 1
        assert local_mcp.sent[0]["subject"] == "Monthly Report"

    def test_social_handoff_workflow(self):
        """Cloud drafts social post -> local publishes after approval."""
        # Step 1: Cloud agent drafts
        cloud_mcp = SimulatedSocialMCP(agent_zone=WorkZone.CLOUD)
        draft_result = cloud_mcp.draft_post(
            platform="instagram",
            content="New product launch!",
        )
        assert draft_result["success"] is True
        draft_id = draft_result["draft_id"]

        # Step 2: Cloud agent attempts publish (should fail)
        with pytest.raises(WorkZoneViolation):
            cloud_mcp.publish_post(draft_id=draft_id, approval_id="appr_301")

        # Step 3: Local agent picks up and publishes
        local_mcp = SimulatedSocialMCP(agent_zone=WorkZone.LOCAL)
        local_mcp.drafts = cloud_mcp.drafts.copy()

        result = local_mcp.publish_post(draft_id=draft_id, approval_id="appr_301")
        assert result["success"] is True
        assert len(local_mcp.published) == 1
        assert local_mcp.published[0]["platform"] == "instagram"

    def test_multiple_drafts_single_handoff(self):
        """Cloud creates multiple drafts, local sends them all."""
        cloud_mcp = SimulatedEmailMCP(agent_zone=WorkZone.CLOUD)

        drafts = []
        for i in range(3):
            result = cloud_mcp.draft_email(
                to=[f"client{i}@example.com"],
                subject=f"Email {i}",
                body=f"Body {i}",
            )
            drafts.append(result["draft_id"])

        assert len(cloud_mcp.drafts) == 3

        # Local agent sends all
        local_mcp = SimulatedEmailMCP(agent_zone=WorkZone.LOCAL)
        local_mcp.drafts = cloud_mcp.drafts.copy()

        for draft_id in drafts:
            result = local_mcp.send_email(
                draft_id=draft_id,
                approval_id=f"appr_{draft_id}",
            )
            assert result["success"] is True

        assert len(local_mcp.sent) == 3
        assert len(local_mcp.drafts) == 0
