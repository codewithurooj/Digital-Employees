"""LoopState model for Ralph Wiggum pause/resume support."""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class LoopStatus(str, Enum):
    """Status of the reasoning loop."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class IterationOutput(BaseModel):
    """Output from a single loop iteration."""
    iteration: int
    timestamp: datetime
    action: str
    result: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class LoopContext(BaseModel):
    """Context preserved during pause/resume."""
    current_file: Optional[str] = None
    pending_actions: list[str] = Field(default_factory=list)
    accumulated_data: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)


class LoopState(BaseModel):
    """Ralph Wiggum loop state with pause/resume support."""

    # Identifiers
    loop_id: str
    prompt: str

    # Progress
    iterations: int = 0
    max_iterations: int = 10
    status: LoopStatus = LoopStatus.PENDING

    # Output history
    output_history: list[IterationOutput] = Field(default_factory=list)

    # Pause state
    paused_at: Optional[datetime] = None
    awaiting_approval: Optional[str] = None  # Approval ID
    approval_reason: Optional[str] = None

    # Context for resume
    context: LoopContext = Field(default_factory=LoopContext)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Platinum Tier: Distributed agent support
    agent_id: Optional[str] = Field(default=None, description="Which agent is running this loop")
    claimed_from: Optional[str] = Field(default=None, description="Original task location")
    sync_required: bool = Field(default=False, description="Git push after completion")

    # Error tracking
    last_error: Optional[str] = None
    error_count: int = 0

    def add_iteration(
        self,
        action: str,
        result: str,
        tool_calls: Optional[list[dict[str, Any]]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Record a new iteration."""
        self.iterations += 1
        self.last_activity = datetime.utcnow()

        output = IterationOutput(
            iteration=self.iterations,
            timestamp=self.last_activity,
            action=action,
            result=result,
            tool_calls=tool_calls or [],
            error=error,
        )
        self.output_history.append(output)

        if error:
            self.error_count += 1
            self.last_error = error

    def pause_for_approval(self, approval_id: str, reason: str) -> None:
        """Pause the loop to wait for approval."""
        self.status = LoopStatus.PAUSED
        self.paused_at = datetime.utcnow()
        self.awaiting_approval = approval_id
        self.approval_reason = reason
        self.last_activity = datetime.utcnow()

    def resume_from_pause(self) -> None:
        """Resume the loop after approval."""
        if self.status != LoopStatus.PAUSED:
            raise ValueError(f"Cannot resume from status: {self.status}")

        self.status = LoopStatus.RUNNING
        self.paused_at = None
        self.awaiting_approval = None
        self.approval_reason = None
        self.last_activity = datetime.utcnow()

    def abort(self, reason: str = "User rejected approval") -> None:
        """Abort the loop on rejection."""
        self.status = LoopStatus.ABORTED
        self.last_error = reason
        self.last_activity = datetime.utcnow()
        self.completed_at = datetime.utcnow()

    def complete(self) -> None:
        """Mark the loop as successfully completed."""
        self.status = LoopStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()

    def fail(self, error: str) -> None:
        """Mark the loop as failed."""
        self.status = LoopStatus.FAILED
        self.last_error = error
        self.error_count += 1
        self.completed_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()

    @property
    def can_continue(self) -> bool:
        """Check if the loop can continue running."""
        return (
            self.status in (LoopStatus.RUNNING, LoopStatus.PENDING)
            and self.iterations < self.max_iterations
        )

    @property
    def is_paused(self) -> bool:
        """Check if loop is waiting for approval."""
        return self.status == LoopStatus.PAUSED

    @property
    def is_finished(self) -> bool:
        """Check if loop has ended (any terminal state)."""
        return self.status in (
            LoopStatus.COMPLETED,
            LoopStatus.FAILED,
            LoopStatus.ABORTED,
        )

    def save(self, vault_path: Path) -> Path:
        """Save loop state to vault."""
        state_file = vault_path / "Plans" / f"LOOP-{self.loop_id}_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2, default=str)

        return state_file

    @classmethod
    def load(cls, vault_path: Path, loop_id: str) -> Optional["LoopState"]:
        """Load loop state from vault."""
        state_file = vault_path / "Plans" / f"LOOP-{loop_id}_state.json"

        if not state_file.exists():
            return None

        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls.model_validate(data)

    @classmethod
    def find_paused_loops(cls, vault_path: Path) -> list["LoopState"]:
        """Find all paused loops in the vault."""
        plans_dir = vault_path / "Plans"
        if not plans_dir.exists():
            return []

        paused = []
        for state_file in plans_dir.glob("LOOP-*_state.json"):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                state = cls.model_validate(data)
                if state.is_paused:
                    paused.append(state)
            except (json.JSONDecodeError, ValueError):
                continue

        return paused

    def cleanup(self, vault_path: Path) -> bool:
        """Remove state file after loop completion."""
        if not self.is_finished:
            return False

        state_file = vault_path / "Plans" / f"LOOP-{self.loop_id}_state.json"
        if state_file.exists():
            state_file.unlink()
            return True
        return False

    def to_summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            f"Loop ID: {self.loop_id}",
            f"Status: {self.status.value}",
            f"Progress: {self.iterations}/{self.max_iterations} iterations",
            f"Prompt: {self.prompt[:100]}{'...' if len(self.prompt) > 100 else ''}",
        ]

        if self.is_paused:
            lines.append(f"Awaiting Approval: {self.awaiting_approval}")
            lines.append(f"Reason: {self.approval_reason}")

        if self.last_error:
            lines.append(f"Last Error: {self.last_error}")

        return "\n".join(lines)
