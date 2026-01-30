"""
Claim-by-move lock implementation for distributed task ownership.

Uses atomic file moves via Git to ensure only one agent can claim a task.
The claim-by-move protocol:
1. Agent detects task in /Needs_Action/{domain}/
2. Agent does: git pull (sync first)
3. Agent moves file to /In_Progress/{agent_id}/
4. Agent adds claim metadata to frontmatter
5. Agent does: git add, commit, push
6. If push succeeds: Agent owns the task
7. If push fails (conflict): Another agent already claimed it
"""

import logging
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from src.models.task_claim import ClaimStatus, TaskClaim

logger = logging.getLogger(__name__)


class ClaimError(Exception):
    """Raised when a claim operation fails."""
    pass


class ClaimConflictError(ClaimError):
    """Raised when another agent has already claimed the task."""
    pass


class ClaimLock:
    """Manages claim-by-move task ownership in the vault."""

    def __init__(self, vault_path: Path, agent_id: str):
        """
        Initialize ClaimLock.

        Args:
            vault_path: Path to the Obsidian vault root
            agent_id: 'cloud' or 'local'
        """
        self.vault_path = Path(vault_path)
        self.agent_id = agent_id
        self.in_progress_dir = self.vault_path / "In_Progress" / agent_id

        # Ensure directories exist
        self.in_progress_dir.mkdir(parents=True, exist_ok=True)

    def claim_task(
        self,
        task_path: Path,
        timeout_minutes: int = 15,
    ) -> TaskClaim:
        """
        Claim a task by moving it to In_Progress/{agent_id}/.

        This is the local filesystem portion of the claim. The caller
        is responsible for the git add/commit/push to make it atomic.

        Args:
            task_path: Absolute path to the task file in Needs_Action
            timeout_minutes: Minutes until claim expires

        Returns:
            TaskClaim record

        Raises:
            ClaimError: If file doesn't exist or can't be moved
            ClaimConflictError: If file is already claimed
        """
        task_path = Path(task_path)

        if not task_path.exists():
            raise ClaimError(f"Task file does not exist: {task_path}")

        # Check if already claimed by any agent
        filename = task_path.name
        for agent_dir in (self.vault_path / "In_Progress").iterdir():
            if agent_dir.is_dir() and (agent_dir / filename).exists():
                raise ClaimConflictError(
                    f"Task already claimed by {agent_dir.name}: {filename}"
                )

        # Read original content
        original_content = task_path.read_text(encoding="utf-8")

        # Extract original type from frontmatter if present
        original_type = ""
        priority = "normal"
        type_match = re.search(r'^type:\s*(.+)$', original_content, re.MULTILINE)
        if type_match:
            original_type = type_match.group(1).strip()
        priority_match = re.search(r'^priority:\s*(.+)$', original_content, re.MULTILINE)
        if priority_match:
            priority = priority_match.group(1).strip()

        # Create claim record
        now = datetime.utcnow()
        claim = TaskClaim(
            original_location=str(task_path.relative_to(self.vault_path)),
            claimed_by=self.agent_id,
            claimed_at=now,
            claim_expires=now + timedelta(minutes=timeout_minutes),
            status=ClaimStatus.IN_PROGRESS,
            original_type=original_type,
            priority=priority,
            task_content=original_content,
        )

        # Move file to In_Progress/{agent_id}/
        dest_path = self.in_progress_dir / filename
        try:
            shutil.move(str(task_path), str(dest_path))
        except OSError as e:
            raise ClaimError(f"Failed to move task file: {e}")

        # Prepend claim frontmatter to the file
        claimed_content = claim.to_frontmatter() + "\n\n" + original_content
        dest_path.write_text(claimed_content, encoding="utf-8")

        logger.info(
            f"Claimed task: {filename} -> In_Progress/{self.agent_id}/ "
            f"(expires {claim.claim_expires.isoformat()})"
        )

        return claim

    def release_task(
        self,
        task_path: Path,
        reason: str = "completed",
        destination: Optional[str] = None,
    ) -> Path:
        """
        Release a claimed task after processing.

        Args:
            task_path: Path to the task in In_Progress/{agent_id}/
            reason: completed, failed, timeout, manual
            destination: Target folder path (relative to vault).
                        Defaults based on reason:
                        - completed -> Done/
                        - failed -> original Needs_Action location
                        - timeout -> original Needs_Action location

        Returns:
            New path of the released file
        """
        task_path = Path(task_path)

        if not task_path.exists():
            raise ClaimError(f"Task file does not exist: {task_path}")

        content = task_path.read_text(encoding="utf-8")

        # Extract original location from claim frontmatter
        original_loc_match = re.search(
            r'^original_location:\s*(.+)$', content, re.MULTILINE
        )
        original_location = original_loc_match.group(1).strip() if original_loc_match else None

        # Determine destination
        if destination:
            dest_dir = self.vault_path / destination
        elif reason == "completed":
            dest_dir = self.vault_path / "Done"
        elif reason in ("failed", "timeout", "manual"):
            if original_location:
                dest_dir = self.vault_path / Path(original_location).parent
            else:
                dest_dir = self.vault_path / "Needs_Action"
        else:
            dest_dir = self.vault_path / "Done"

        dest_dir.mkdir(parents=True, exist_ok=True)

        # Move file
        dest_path = dest_dir / task_path.name
        shutil.move(str(task_path), str(dest_path))

        logger.info(f"Released task: {task_path.name} -> {dest_dir} (reason: {reason})")

        return dest_path

    def release_to_approval(
        self,
        task_path: Path,
        domain: str = "",
    ) -> Path:
        """
        Move a claimed task to Pending_Approval for human review.

        Args:
            task_path: Path to the task in In_Progress/{agent_id}/
            domain: Domain subfolder (email, accounting, social, payments)

        Returns:
            New path in Pending_Approval/
        """
        if domain:
            dest_dir = self.vault_path / "Pending_Approval" / domain
        else:
            dest_dir = self.vault_path / "Pending_Approval"

        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / Path(task_path).name
        shutil.move(str(task_path), str(dest_path))

        logger.info(f"Moved to approval: {task_path} -> {dest_path}")
        return dest_path

    def get_active_claims(self) -> list[Path]:
        """Get all active claims for this agent."""
        if not self.in_progress_dir.exists():
            return []
        return [
            f for f in self.in_progress_dir.iterdir()
            if f.is_file() and f.suffix == ".md"
        ]

    def release_expired_claims(self) -> list[Path]:
        """Release all expired claims back to their original locations."""
        released = []
        for claim_file in self.get_active_claims():
            content = claim_file.read_text(encoding="utf-8")
            expires_match = re.search(
                r'^claim_expires:\s*(.+)$', content, re.MULTILINE
            )
            if expires_match:
                try:
                    expires_at = datetime.fromisoformat(expires_match.group(1).strip())
                    if datetime.utcnow() > expires_at:
                        new_path = self.release_task(
                            claim_file, reason="timeout"
                        )
                        released.append(new_path)
                        logger.warning(
                            f"Released expired claim: {claim_file.name}"
                        )
                except (ValueError, TypeError):
                    pass
        return released
