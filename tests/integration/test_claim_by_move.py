"""Integration tests for the claim-by-move task ownership protocol."""

import pytest
from pathlib import Path

from src.utils.claim_lock import ClaimLock, ClaimError, ClaimConflictError


class TestClaimByMove:
    """Test claim-by-move protocol for task ownership."""

    def test_claim_task_moves_file(self, platinum_vault, sample_task_file):
        """Claiming a task should move it to In_Progress/{agent_id}/."""
        lock = ClaimLock(platinum_vault, "cloud")
        claim = lock.claim_task(sample_task_file)

        # File should be moved
        assert not sample_task_file.exists()
        claimed_path = platinum_vault / "In_Progress" / "cloud" / sample_task_file.name
        assert claimed_path.exists()

        # Claim record should have correct data
        assert claim.claimed_by == "cloud"
        assert claim.original_location == str(
            sample_task_file.relative_to(platinum_vault)
        )

    def test_claim_adds_frontmatter(self, platinum_vault, sample_task_file):
        """Claimed file should have claim metadata in frontmatter."""
        lock = ClaimLock(platinum_vault, "cloud")
        lock.claim_task(sample_task_file)

        claimed_path = platinum_vault / "In_Progress" / "cloud" / sample_task_file.name
        content = claimed_path.read_text(encoding="utf-8")
        assert "type: task_claim" in content
        assert "claimed_by: cloud" in content

    def test_cannot_claim_nonexistent_file(self, platinum_vault):
        """Claiming a nonexistent file should raise ClaimError."""
        lock = ClaimLock(platinum_vault, "cloud")
        fake_path = platinum_vault / "Needs_Action" / "email" / "NONEXISTENT.md"

        with pytest.raises(ClaimError):
            lock.claim_task(fake_path)

    def test_cannot_claim_already_claimed(self, platinum_vault, sample_task_file):
        """Claiming an already-claimed task should raise ClaimConflictError."""
        # Cloud agent claims first
        cloud_lock = ClaimLock(platinum_vault, "cloud")
        cloud_lock.claim_task(sample_task_file)

        # Local agent tries to claim the same task
        local_lock = ClaimLock(platinum_vault, "local")
        claimed_path = platinum_vault / "In_Progress" / "cloud" / sample_task_file.name

        with pytest.raises(ClaimConflictError):
            local_lock.claim_task(claimed_path)

    def test_release_completed_task(self, platinum_vault, sample_task_file):
        """Releasing a completed task should move it to Done/."""
        lock = ClaimLock(platinum_vault, "cloud")
        lock.claim_task(sample_task_file)

        claimed_path = platinum_vault / "In_Progress" / "cloud" / sample_task_file.name
        new_path = lock.release_task(claimed_path, reason="completed")

        assert not claimed_path.exists()
        assert new_path.parent.name == "Done"
        assert new_path.exists()

    def test_release_failed_task(self, platinum_vault, sample_task_file):
        """Releasing a failed task should move it back to Needs_Action."""
        lock = ClaimLock(platinum_vault, "cloud")
        lock.claim_task(sample_task_file)

        claimed_path = platinum_vault / "In_Progress" / "cloud" / sample_task_file.name
        new_path = lock.release_task(claimed_path, reason="failed")

        assert not claimed_path.exists()
        assert new_path.exists()

    def test_release_to_approval(self, platinum_vault, sample_task_file):
        """Should move task to Pending_Approval/{domain}/."""
        lock = ClaimLock(platinum_vault, "cloud")
        lock.claim_task(sample_task_file)

        claimed_path = platinum_vault / "In_Progress" / "cloud" / sample_task_file.name
        approval_path = lock.release_to_approval(claimed_path, domain="email")

        assert not claimed_path.exists()
        assert approval_path.exists()
        assert "Pending_Approval" in str(approval_path)
        assert "email" in str(approval_path)

    def test_get_active_claims(self, platinum_vault, sample_task_file):
        """Should list all active claims for the agent."""
        lock = ClaimLock(platinum_vault, "cloud")
        lock.claim_task(sample_task_file)

        claims = lock.get_active_claims()
        assert len(claims) == 1
        assert claims[0].name == sample_task_file.name
