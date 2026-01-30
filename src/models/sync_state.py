"""SyncState model for Git synchronization tracking."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class SyncOperation(BaseModel):
    """Record of a single sync operation."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    commit_hash: str = Field(default="")
    files_changed: int = Field(default=0)
    success: bool = Field(default=True)
    error: Optional[str] = None


class SyncState(BaseModel):
    """Tracks Git synchronization status and history."""

    agent_id: str = Field(description="'cloud' or 'local'")
    last_pull: Optional[SyncOperation] = None
    last_push: Optional[SyncOperation] = None
    sync_interval_seconds: int = Field(default=30, ge=10, le=300)
    consecutive_failures: int = Field(default=0, ge=0)
    total_syncs_today: int = Field(default=0, ge=0)
    conflicts_resolved_today: int = Field(default=0, ge=0)
    pending_changes: list[str] = Field(default_factory=list)
    remote_url: str = Field(default="")
    branch: str = Field(default="main")

    def record_pull(self, commit_hash: str, files_changed: int = 0) -> None:
        """Record a successful pull operation."""
        self.last_pull = SyncOperation(
            commit_hash=commit_hash,
            files_changed=files_changed,
        )
        self.consecutive_failures = 0
        self.total_syncs_today += 1

    def record_push(self, commit_hash: str, files_added: int = 0) -> None:
        """Record a successful push operation."""
        self.last_push = SyncOperation(
            commit_hash=commit_hash,
            files_changed=files_added,
        )
        self.consecutive_failures = 0
        self.total_syncs_today += 1
        self.pending_changes.clear()

    def record_failure(self, error: str) -> None:
        """Record a failed sync operation."""
        self.consecutive_failures += 1

    @property
    def needs_alert(self) -> bool:
        """Check if consecutive failures warrant an alert."""
        return self.consecutive_failures >= 5

    def save(self, vault_path: Path) -> Path:
        """Save sync state to vault Health folder."""
        state_file = vault_path / "Health" / "sync_state.json"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(mode="json"), f, indent=2, default=str)
        return state_file

    @classmethod
    def load(cls, vault_path: Path) -> Optional["SyncState"]:
        """Load sync state from vault."""
        state_file = vault_path / "Health" / "sync_state.json"
        if not state_file.exists():
            return None
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)
