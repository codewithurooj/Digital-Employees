"""AgentIdentity model for distributed agent identification."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WorkZone(str, Enum):
    """Work zone determines agent permissions."""
    CLOUD = "cloud"
    LOCAL = "local"


class AgentIdentity(BaseModel):
    """Identifies which agent (cloud or local) is performing operations."""

    agent_id: str = Field(description="'cloud' or 'local'")
    work_zone: WorkZone = Field(description="Determines permissions")
    hostname: str = Field(default="", description="VM/machine hostname")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="", description="Code version/commit hash")
    capabilities: list[str] = Field(default_factory=list)
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)
    active_tasks: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)

    @classmethod
    def cloud(cls, hostname: str = "", version: str = "") -> "AgentIdentity":
        """Create a cloud agent identity."""
        return cls(
            agent_id="cloud",
            work_zone=WorkZone.CLOUD,
            hostname=hostname,
            version=version,
            capabilities=[
                "read_vault",
                "write_needs_action",
                "write_drafts",
                "sync_git",
            ],
        )

    @classmethod
    def local(cls, hostname: str = "", version: str = "") -> "AgentIdentity":
        """Create a local agent identity."""
        return cls(
            agent_id="local",
            work_zone=WorkZone.LOCAL,
            hostname=hostname,
            version=version,
            capabilities=[
                "read_vault",
                "write_needs_action",
                "write_drafts",
                "sync_git",
                "execute_approval",
                "send_email",
                "post_social",
                "process_payment",
                "whatsapp_operations",
            ],
        )

    def heartbeat(self) -> None:
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()

    def record_error(self) -> None:
        """Increment the error count."""
        self.error_count += 1

    def clear_errors(self) -> None:
        """Reset the error count."""
        self.error_count = 0

    @property
    def is_cloud(self) -> bool:
        return self.work_zone == WorkZone.CLOUD

    @property
    def is_local(self) -> bool:
        return self.work_zone == WorkZone.LOCAL

    def has_capability(self, capability: str) -> bool:
        """Check if agent has a specific capability."""
        return capability in self.capabilities
