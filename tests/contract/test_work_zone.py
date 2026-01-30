"""
Contract tests for work-zone enforcement (T039).

Validates that the WorkZone module correctly enforces cloud/local boundaries:
- @requires_local blocks cloud agents from executing local-only actions
- @requires_local allows local agents and backwards-compat (None zone)
- WorkZoneViolation carries action, zone, required fields
- CLOUD_ALLOWED / CLOUD_BLOCKED frozensets contain expected actions
- Helper functions is_cloud_allowed / is_cloud_blocked work correctly
- get_zone_from_env reads WORK_ZONE env var
"""

import os
import pytest

from src.cloud.work_zone import (
    WorkZone,
    WorkZoneViolation,
    requires_local,
    CLOUD_ALLOWED,
    CLOUD_BLOCKED,
    is_cloud_allowed,
    is_cloud_blocked,
    get_zone_from_env,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MockMCP:
    """Mock MCP server to test the @requires_local decorator."""

    def __init__(self, zone=None):
        self.agent_zone = zone
        self.calls = []
        self.audit_events = []

    @requires_local
    def send_action(self, data):
        self.calls.append(data)
        return "sent"

    def draft_action(self, data):
        self.calls.append(data)
        return "drafted"

    def audit_log(self, event_type, details):
        """Mock audit_log for testing violation logging."""
        self.audit_events.append({"event_type": event_type, "details": details})


# ---------------------------------------------------------------------------
# @requires_local decorator tests
# ---------------------------------------------------------------------------

class TestRequiresLocalDecorator:
    """Tests for the @requires_local decorator."""

    def test_blocks_cloud_agent(self):
        """Cloud agent must be blocked from executing local-only actions."""
        mcp = MockMCP(zone=WorkZone.CLOUD)

        with pytest.raises(WorkZoneViolation) as exc_info:
            mcp.send_action("test_data")

        assert exc_info.value.action == "send_action"
        assert exc_info.value.zone == "cloud"
        assert exc_info.value.required == "local"
        # The action must not have executed
        assert mcp.calls == []

    def test_allows_local_agent(self):
        """Local agent must be allowed to execute local-only actions."""
        mcp = MockMCP(zone=WorkZone.LOCAL)

        result = mcp.send_action("test_data")

        assert result == "sent"
        assert mcp.calls == ["test_data"]

    def test_allows_none_zone_backwards_compat(self):
        """When agent_zone is None, execution must be allowed (backwards compat)."""
        mcp = MockMCP(zone=None)

        result = mcp.send_action("test_data")

        assert result == "sent"
        assert mcp.calls == ["test_data"]

    def test_allows_missing_agent_zone_attribute(self):
        """When agent_zone attribute is completely absent, must be allowed."""

        class BareClass:
            @requires_local
            def do_thing(self):
                return "done"

        obj = BareClass()
        assert obj.do_thing() == "done"

    def test_decorated_function_preserves_name(self):
        """The decorator must preserve the wrapped function's __name__."""
        mcp = MockMCP()
        assert mcp.send_action.__name__ == "send_action"

    def test_decorated_function_has_requires_local_marker(self):
        """Decorated functions must have _requires_local = True."""
        mcp = MockMCP()
        assert getattr(mcp.send_action, "_requires_local", False) is True

    def test_audit_log_called_on_violation(self):
        """When audit_log method exists, it must be called on violation."""
        mcp = MockMCP(zone=WorkZone.CLOUD)

        with pytest.raises(WorkZoneViolation):
            mcp.send_action("test_data")

        assert len(mcp.audit_events) == 1
        event = mcp.audit_events[0]
        assert event["event_type"] == "work_zone_violation"
        assert event["details"]["action"] == "send_action"
        assert event["details"]["zone"] == "cloud"
        assert event["details"]["required"] == "local"


# ---------------------------------------------------------------------------
# WorkZoneViolation exception tests
# ---------------------------------------------------------------------------

class TestWorkZoneViolation:
    """Tests for the WorkZoneViolation exception."""

    def test_contains_required_fields(self):
        """Violation must carry action, zone, and required fields."""
        exc = WorkZoneViolation(action="send_email", zone="cloud", required="local")

        assert exc.action == "send_email"
        assert exc.zone == "cloud"
        assert exc.required == "local"

    def test_message_format(self):
        """Violation message must include action, zone, and required info."""
        exc = WorkZoneViolation(action="post_social", zone="cloud", required="local")
        msg = str(exc)

        assert "post_social" in msg
        assert "cloud" in msg
        assert "local" in msg

    def test_is_exception(self):
        """WorkZoneViolation must be an Exception."""
        exc = WorkZoneViolation(action="test", zone="cloud", required="local")
        assert isinstance(exc, Exception)


# ---------------------------------------------------------------------------
# WorkZone enum tests
# ---------------------------------------------------------------------------

class TestWorkZoneEnum:
    """Tests for the WorkZone enum."""

    def test_cloud_value(self):
        assert WorkZone.CLOUD.value == "cloud"

    def test_local_value(self):
        assert WorkZone.LOCAL.value == "local"

    def test_is_str_enum(self):
        """WorkZone values must be usable as strings."""
        assert WorkZone.CLOUD == "cloud"
        assert WorkZone.LOCAL == "local"


# ---------------------------------------------------------------------------
# CLOUD_ALLOWED / CLOUD_BLOCKED frozenset tests
# ---------------------------------------------------------------------------

class TestCloudAllowedBlocked:
    """Tests for CLOUD_ALLOWED and CLOUD_BLOCKED frozensets."""

    def test_cloud_allowed_contains_read_vault(self):
        assert "read_vault" in CLOUD_ALLOWED

    def test_cloud_allowed_contains_draft_email(self):
        assert "draft_email" in CLOUD_ALLOWED

    def test_cloud_allowed_contains_draft_invoice(self):
        assert "draft_invoice" in CLOUD_ALLOWED

    def test_cloud_allowed_contains_draft_social_post(self):
        assert "draft_social_post" in CLOUD_ALLOWED

    def test_cloud_allowed_contains_read_api_gmail(self):
        assert "read_api_gmail" in CLOUD_ALLOWED

    def test_cloud_allowed_contains_read_api_odoo(self):
        assert "read_api_odoo" in CLOUD_ALLOWED

    def test_cloud_allowed_contains_sync_git(self):
        assert "sync_git" in CLOUD_ALLOWED

    def test_cloud_allowed_contains_generate_summary(self):
        assert "generate_summary" in CLOUD_ALLOWED

    def test_cloud_allowed_contains_triage_email(self):
        assert "triage_email" in CLOUD_ALLOWED

    def test_cloud_blocked_contains_send_email(self):
        assert "send_email" in CLOUD_BLOCKED

    def test_cloud_blocked_contains_post_social(self):
        assert "post_social" in CLOUD_BLOCKED

    def test_cloud_blocked_contains_execute_payment(self):
        assert "execute_payment" in CLOUD_BLOCKED

    def test_cloud_blocked_contains_approve_request(self):
        assert "approve_request" in CLOUD_BLOCKED

    def test_cloud_blocked_contains_write_dashboard(self):
        assert "write_dashboard" in CLOUD_BLOCKED

    def test_cloud_blocked_contains_whatsapp_any_operation(self):
        assert "whatsapp_any_operation" in CLOUD_BLOCKED

    def test_cloud_blocked_contains_banking_any_operation(self):
        assert "banking_any_operation" in CLOUD_BLOCKED

    def test_cloud_blocked_contains_publish_social_post(self):
        assert "publish_social_post" in CLOUD_BLOCKED

    def test_cloud_blocked_contains_post_invoice(self):
        assert "post_invoice" in CLOUD_BLOCKED

    def test_cloud_blocked_contains_post_payment(self):
        assert "post_payment" in CLOUD_BLOCKED

    def test_no_overlap_between_allowed_and_blocked(self):
        """CLOUD_ALLOWED and CLOUD_BLOCKED must not overlap."""
        overlap = CLOUD_ALLOWED & CLOUD_BLOCKED
        assert len(overlap) == 0, f"Overlapping actions: {overlap}"

    def test_frozensets_are_immutable(self):
        """Both sets must be frozenset (immutable)."""
        assert isinstance(CLOUD_ALLOWED, frozenset)
        assert isinstance(CLOUD_BLOCKED, frozenset)


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestHelperFunctions:
    """Tests for is_cloud_allowed and is_cloud_blocked."""

    def test_is_cloud_allowed_returns_true_for_allowed_action(self):
        assert is_cloud_allowed("read_vault") is True

    def test_is_cloud_allowed_returns_false_for_blocked_action(self):
        assert is_cloud_allowed("send_email") is False

    def test_is_cloud_allowed_returns_false_for_unknown_action(self):
        assert is_cloud_allowed("nonexistent_action") is False

    def test_is_cloud_blocked_returns_true_for_blocked_action(self):
        assert is_cloud_blocked("send_email") is True

    def test_is_cloud_blocked_returns_false_for_allowed_action(self):
        assert is_cloud_blocked("read_vault") is False

    def test_is_cloud_blocked_returns_false_for_unknown_action(self):
        assert is_cloud_blocked("nonexistent_action") is False


# ---------------------------------------------------------------------------
# get_zone_from_env tests
# ---------------------------------------------------------------------------

class TestGetZoneFromEnv:
    """Tests for get_zone_from_env."""

    def test_returns_cloud_when_env_is_cloud(self, monkeypatch):
        monkeypatch.setenv("WORK_ZONE", "cloud")
        assert get_zone_from_env() == WorkZone.CLOUD

    def test_returns_local_when_env_is_local(self, monkeypatch):
        monkeypatch.setenv("WORK_ZONE", "local")
        assert get_zone_from_env() == WorkZone.LOCAL

    def test_returns_local_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("WORK_ZONE", raising=False)
        assert get_zone_from_env() == WorkZone.LOCAL

    def test_returns_local_for_invalid_value(self, monkeypatch):
        monkeypatch.setenv("WORK_ZONE", "invalid_zone")
        assert get_zone_from_env() == WorkZone.LOCAL
