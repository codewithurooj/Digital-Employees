"""TaskClaim model for claim-by-move task ownership protocol."""

from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    """Status of a task claim."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    RELEASED = "released"
    EXPIRED = "expired"


class TaskClaim(BaseModel):
    """Records task ownership via claim-by-move protocol."""

    original_location: str = Field(description="Original path in Needs_Action")
    claimed_by: str = Field(description="Agent ID that claimed the task")
    claimed_at: datetime = Field(default_factory=datetime.utcnow)
    claim_expires: datetime = Field(default=None, description="15 min timeout")
    status: ClaimStatus = Field(default=ClaimStatus.IN_PROGRESS)
    original_type: str = Field(default="", description="Original task type")
    priority: str = Field(default="normal")
    task_content: str = Field(default="", description="Original task content")

    def model_post_init(self, __context) -> None:
        if self.claim_expires is None:
            self.claim_expires = self.claimed_at + timedelta(minutes=15)

    @property
    def is_expired(self) -> bool:
        """Check if the claim has expired."""
        return datetime.utcnow() > self.claim_expires

    @property
    def is_active(self) -> bool:
        """Check if the claim is still active."""
        return self.status == ClaimStatus.IN_PROGRESS and not self.is_expired

    def complete(self) -> None:
        """Mark the claim as completed."""
        self.status = ClaimStatus.COMPLETED

    def release(self) -> None:
        """Release the claim back to the queue."""
        self.status = ClaimStatus.RELEASED

    def expire(self) -> None:
        """Mark the claim as expired."""
        self.status = ClaimStatus.EXPIRED

    def to_frontmatter(self) -> str:
        """Generate YAML frontmatter for the claimed file."""
        return f"""---
type: task_claim
original_location: {self.original_location}
claimed_by: {self.claimed_by}
claimed_at: {self.claimed_at.isoformat()}
claim_expires: {self.claim_expires.isoformat()}
status: {self.status.value}
original_type: {self.original_type}
priority: {self.priority}
---"""

    def claimed_path(self, vault_path: Path) -> Path:
        """Get the path where the claimed file should be."""
        filename = Path(self.original_location).name
        return vault_path / "In_Progress" / self.claimed_by / filename
