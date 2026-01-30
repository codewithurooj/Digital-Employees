"""
Work-Zone Specialization for Cloud/Local Agent Boundaries.

Defines clear boundaries between what cloud and local agents can do.
Cloud agent operates in draft-only mode; local agent has full execution capability.

Usage:
    from src.cloud.work_zone import WorkZone, requires_local, WorkZoneViolation

    class EmailMCP:
        def __init__(self, agent_zone: WorkZone):
            self.agent_zone = agent_zone

        def draft_email(self, to, subject, body):
            # Both agents can draft
            ...

        @requires_local
        def send_email(self, draft_id):
            # Only local agent can send
            ...
"""

import logging
from enum import Enum
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)


class WorkZone(str, Enum):
    """Agent work zone determines permissions."""
    CLOUD = "cloud"
    LOCAL = "local"


class WorkZoneViolation(Exception):
    """Raised when an agent attempts an action outside its work zone."""

    def __init__(self, action: str, zone: str, required: str):
        self.action = action
        self.zone = zone
        self.required = required
        super().__init__(
            f"Work-zone violation: '{action}' requires {required} agent, "
            f"but current zone is {zone}"
        )


# Actions allowed for cloud agent
CLOUD_ALLOWED = frozenset([
    "read_vault",
    "write_needs_action",
    "write_drafts",
    "write_updates",
    "write_in_progress_cloud",
    "create_approval_request",
    "sync_git",
    "read_api_gmail",
    "read_api_odoo",
    "draft_email",
    "draft_invoice",
    "draft_social_post",
    "triage_email",
    "generate_summary",
])

# Actions blocked for cloud agent (local-only)
CLOUD_BLOCKED = frozenset([
    "send_email",
    "post_social",
    "execute_payment",
    "approve_request",
    "write_dashboard",
    "write_in_progress_local",
    "whatsapp_any_operation",
    "banking_any_operation",
    "post_invoice",
    "post_payment",
    "publish_social_post",
])


def requires_local(func: Callable) -> Callable:
    """
    Decorator to enforce local-only execution.

    The decorated method's instance must have an `agent_zone` attribute
    set to a WorkZone enum value.

    Raises:
        WorkZoneViolation: If called from cloud agent
    """

    @wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        zone = getattr(self, "agent_zone", None)
        if zone is None:
            # No zone set, allow execution (backwards compatibility)
            return func(self, *args, **kwargs)

        if zone == WorkZone.CLOUD:
            violation = WorkZoneViolation(
                action=func.__name__,
                zone="cloud",
                required="local",
            )
            logger.warning(
                f"BLOCKED: {func.__name__} requires local agent "
                f"(current zone: cloud)"
            )
            # Log audit event if audit_log method exists
            audit_log = getattr(self, "audit_log", None)
            if callable(audit_log):
                audit_log("work_zone_violation", {
                    "action": func.__name__,
                    "zone": "cloud",
                    "required": "local",
                })
            raise violation

        return func(self, *args, **kwargs)

    # Mark the function as requiring local execution
    wrapper._requires_local = True
    return wrapper


def is_cloud_allowed(action: str) -> bool:
    """Check if an action is allowed for the cloud agent."""
    return action in CLOUD_ALLOWED


def is_cloud_blocked(action: str) -> bool:
    """Check if an action is blocked for the cloud agent."""
    return action in CLOUD_BLOCKED


def get_zone_from_env() -> WorkZone:
    """Get the work zone from environment variables."""
    import os
    zone = os.environ.get("WORK_ZONE", "local")
    try:
        return WorkZone(zone)
    except ValueError:
        logger.warning(f"Invalid WORK_ZONE '{zone}', defaulting to LOCAL")
        return WorkZone.LOCAL
