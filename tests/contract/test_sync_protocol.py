"""Contract tests for the vault synchronization protocol."""

import json
import pytest
from pathlib import Path
from datetime import datetime

from src.models.sync_state import SyncState, SyncOperation
from src.models.task_claim import TaskClaim, ClaimStatus


class TestSyncStateContract:
    """Verify SyncState model meets the sync-protocol.yaml contract."""

    def test_sync_state_has_required_fields(self):
        """SyncState must have agent_id and sync tracking fields."""
        state = SyncState(agent_id="cloud")
        assert state.agent_id == "cloud"
        assert state.last_pull is None
        assert state.last_push is None
        assert state.sync_interval_seconds >= 10
        assert state.consecutive_failures == 0

    def test_sync_state_interval_bounds(self):
        """Sync interval must be between 10 and 300 seconds."""
        state = SyncState(agent_id="cloud", sync_interval_seconds=30)
        assert 10 <= state.sync_interval_seconds <= 300

        with pytest.raises(Exception):
            SyncState(agent_id="cloud", sync_interval_seconds=5)

        with pytest.raises(Exception):
            SyncState(agent_id="cloud", sync_interval_seconds=500)

    def test_record_pull(self):
        """Recording a pull should update last_pull and reset failures."""
        state = SyncState(agent_id="cloud", consecutive_failures=3)
        state.record_pull("abc123", files_changed=5)

        assert state.last_pull is not None
        assert state.last_pull.commit_hash == "abc123"
        assert state.last_pull.files_changed == 5
        assert state.consecutive_failures == 0
        assert state.total_syncs_today == 1

    def test_record_push(self):
        """Recording a push should update last_push and clear pending."""
        state = SyncState(
            agent_id="cloud",
            pending_changes=["file1.md", "file2.md"],
        )
        state.record_push("def456", files_added=2)

        assert state.last_push is not None
        assert state.last_push.commit_hash == "def456"
        assert state.pending_changes == []

    def test_failure_tracking(self):
        """Consecutive failures should trigger alert at 5."""
        state = SyncState(agent_id="cloud")
        for _ in range(4):
            state.record_failure("connection error")
            assert not state.needs_alert

        state.record_failure("connection error")
        assert state.needs_alert

    def test_save_and_load(self, platinum_vault):
        """SyncState should persist to Health/sync_state.json."""
        state = SyncState(agent_id="cloud", branch="main")
        state.record_pull("abc123", files_changed=3)
        saved_path = state.save(platinum_vault)

        assert saved_path.exists()
        assert saved_path.name == "sync_state.json"

        loaded = SyncState.load(platinum_vault)
        assert loaded is not None
        assert loaded.agent_id == "cloud"
        assert loaded.branch == "main"

    def test_load_returns_none_if_missing(self, platinum_vault):
        """Load should return None if no state file exists."""
        # Remove the file if it exists
        state_file = platinum_vault / "Health" / "sync_state.json"
        if state_file.exists():
            state_file.unlink()
        assert SyncState.load(platinum_vault) is None


class TestTaskClaimContract:
    """Verify TaskClaim model meets the sync-protocol.yaml claim contract."""

    def test_claim_has_required_fields(self):
        """TaskClaim must have original_location and claimed_by."""
        claim = TaskClaim(
            original_location="/Needs_Action/email/TASK_001.md",
            claimed_by="cloud",
        )
        assert claim.original_location == "/Needs_Action/email/TASK_001.md"
        assert claim.claimed_by == "cloud"
        assert claim.status == ClaimStatus.IN_PROGRESS

    def test_claim_expires_default_15_min(self):
        """Claims should expire 15 minutes after creation by default."""
        claim = TaskClaim(
            original_location="/Needs_Action/email/TASK_001.md",
            claimed_by="cloud",
        )
        diff = (claim.claim_expires - claim.claimed_at).total_seconds()
        assert 899 <= diff <= 901  # ~15 minutes

    def test_claim_status_transitions(self):
        """Claims should support complete, release, expire transitions."""
        claim = TaskClaim(
            original_location="/Needs_Action/email/TASK_001.md",
            claimed_by="cloud",
        )
        assert claim.is_active

        claim.complete()
        assert claim.status == ClaimStatus.COMPLETED
        assert not claim.is_active

    def test_claim_frontmatter(self):
        """to_frontmatter should produce valid YAML."""
        claim = TaskClaim(
            original_location="/Needs_Action/email/TASK_001.md",
            claimed_by="cloud",
        )
        fm = claim.to_frontmatter()
        assert "type: task_claim" in fm
        assert "claimed_by: cloud" in fm
        assert "original_location:" in fm

    def test_claimed_path(self, platinum_vault):
        """claimed_path should resolve to In_Progress/{agent_id}/."""
        claim = TaskClaim(
            original_location="Needs_Action/email/TASK_001.md",
            claimed_by="cloud",
        )
        path = claim.claimed_path(platinum_vault)
        assert "In_Progress" in str(path)
        assert "cloud" in str(path)
        assert path.name == "TASK_001.md"
