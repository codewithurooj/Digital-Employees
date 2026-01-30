"""Integration tests for Git conflict resolution in vault sync."""

import pytest
from pathlib import Path

from src.utils.claim_lock import ClaimLock, ClaimConflictError


class TestConflictResolution:
    """Test conflict resolution scenarios between cloud and local agents."""

    def test_first_mover_wins_claim(self, platinum_vault, sample_task_file):
        """When both agents try to claim, first mover wins."""
        cloud_lock = ClaimLock(platinum_vault, "cloud")
        local_lock = ClaimLock(platinum_vault, "local")

        # Cloud claims first
        cloud_claim = cloud_lock.claim_task(sample_task_file)
        assert cloud_claim.claimed_by == "cloud"

        # File no longer exists at original location
        assert not sample_task_file.exists()

        # Local cannot claim (file is gone)
        with pytest.raises(Exception):
            local_lock.claim_task(sample_task_file)

    def test_independent_claims_no_conflict(self, platinum_vault):
        """Two agents claiming different tasks should not conflict."""
        # Create two task files
        task1 = platinum_vault / "Needs_Action" / "email" / "TASK_001.md"
        task1.write_text("---\ntype: email\n---\nTask 1", encoding="utf-8")

        task2 = platinum_vault / "Needs_Action" / "accounting" / "TASK_002.md"
        task2.write_text("---\ntype: invoice\n---\nTask 2", encoding="utf-8")

        cloud_lock = ClaimLock(platinum_vault, "cloud")
        local_lock = ClaimLock(platinum_vault, "local")

        cloud_claim = cloud_lock.claim_task(task1)
        local_claim = local_lock.claim_task(task2)

        assert cloud_claim.claimed_by == "cloud"
        assert local_claim.claimed_by == "local"

        # Both should be in their respective In_Progress folders
        assert (platinum_vault / "In_Progress" / "cloud" / "TASK_001.md").exists()
        assert (platinum_vault / "In_Progress" / "local" / "TASK_002.md").exists()

    def test_expired_claim_can_be_reclaimed(self, platinum_vault, sample_task_file):
        """After a claim expires, another agent can claim the task."""
        from datetime import datetime, timedelta

        cloud_lock = ClaimLock(platinum_vault, "cloud")
        claim = cloud_lock.claim_task(sample_task_file, timeout_minutes=0)

        # Force expiration by checking
        assert claim.is_expired

        # Release expired claims
        cloud_lock.release_expired_claims()

        # Now local should be able to claim it from its returned location
        # The file should be back in Needs_Action
        returned_files = list((platinum_vault / "Needs_Action").rglob("TASK_20260128_001.md"))
        assert len(returned_files) > 0

    def test_multiple_claims_same_agent(self, platinum_vault):
        """Same agent should be able to claim multiple tasks."""
        lock = ClaimLock(platinum_vault, "cloud")

        task1 = platinum_vault / "Needs_Action" / "email" / "TASK_A.md"
        task1.write_text("Task A content", encoding="utf-8")

        task2 = platinum_vault / "Needs_Action" / "email" / "TASK_B.md"
        task2.write_text("Task B content", encoding="utf-8")

        lock.claim_task(task1)
        lock.claim_task(task2)

        claims = lock.get_active_claims()
        assert len(claims) == 2
