"""
Git-based Vault Synchronization Manager.

Handles Git operations for syncing the Obsidian vault between
cloud and local agents. Implements the sync protocol defined
in contracts/sync-protocol.yaml.
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.models.sync_state import SyncState

logger = logging.getLogger(__name__)


class SyncError(Exception):
    """Raised when a sync operation fails."""
    pass


class SyncConflictError(SyncError):
    """Raised when a Git conflict is detected."""
    def __init__(self, conflicting_files: list[str]):
        self.conflicting_files = conflicting_files
        super().__init__(f"Sync conflict in files: {conflicting_files}")


class SyncManager:
    """Manages Git-based vault synchronization."""

    def __init__(
        self,
        vault_path: Path,
        agent_id: str = "cloud",
        remote: str = "origin",
        branch: str = "main",
    ):
        self.vault_path = Path(vault_path)
        self.agent_id = agent_id
        self.remote = remote
        self.branch = branch
        self.state = SyncState.load(self.vault_path) or SyncState(
            agent_id=agent_id,
            remote_url="",
            branch=branch,
        )

    def _run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the vault directory."""
        cmd = ["git"] + list(args)
        logger.debug(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.vault_path),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if check and result.returncode != 0:
                logger.error(f"Git error: {result.stderr.strip()}")
            return result
        except subprocess.TimeoutExpired:
            raise SyncError("Git command timed out after 60 seconds")
        except FileNotFoundError:
            raise SyncError("Git is not installed or not in PATH")

    def _get_head_hash(self) -> str:
        """Get the current HEAD commit hash."""
        result = self._run_git("rev-parse", "HEAD", check=False)
        return result.stdout.strip() if result.returncode == 0 else ""

    def pull_changes(self) -> dict:
        """
        Pull latest changes from remote repository.

        Returns:
            Dict with success, commit_hash, files_updated, conflicts
        """
        result_data = {
            "success": False,
            "timestamp": datetime.utcnow().isoformat(),
            "commit_hash": "",
            "files_updated": [],
            "conflicts": [],
        }

        try:
            # Fetch first to check for changes
            fetch_result = self._run_git("fetch", self.remote, self.branch, check=False)
            if fetch_result.returncode != 0:
                self.state.record_failure(fetch_result.stderr.strip())
                self.state.save(self.vault_path)
                return result_data

            # Pull with rebase=false (merge strategy)
            pull_result = self._run_git(
                "pull", "--no-edit", self.remote, self.branch, check=False
            )

            if pull_result.returncode == 0:
                result_data["success"] = True
                result_data["commit_hash"] = self._get_head_hash()

                # Parse changed files from output
                if "file changed" in pull_result.stdout or "files changed" in pull_result.stdout:
                    diff_result = self._run_git(
                        "diff", "--name-only", "HEAD~1", "HEAD", check=False
                    )
                    if diff_result.returncode == 0:
                        result_data["files_updated"] = [
                            f.strip() for f in diff_result.stdout.strip().split("\n") if f.strip()
                        ]

                self.state.record_pull(
                    result_data["commit_hash"],
                    files_changed=len(result_data["files_updated"]),
                )
                logger.info(
                    f"Pull successful: {len(result_data['files_updated'])} files updated"
                )

            elif "CONFLICT" in pull_result.stdout or "CONFLICT" in pull_result.stderr:
                # Handle conflicts
                conflict_output = pull_result.stdout + pull_result.stderr
                conflicting = [
                    line.split(":")[-1].strip()
                    for line in conflict_output.split("\n")
                    if "CONFLICT" in line
                ]
                result_data["conflicts"] = conflicting
                self.state.record_failure("merge conflict")
                logger.warning(f"Pull conflict in files: {conflicting}")

                # Abort the merge
                self._run_git("merge", "--abort", check=False)

            else:
                self.state.record_failure(pull_result.stderr.strip())
                logger.error(f"Pull failed: {pull_result.stderr.strip()}")

        except SyncError as e:
            self.state.record_failure(str(e))
            logger.error(f"Pull error: {e}")

        self.state.save(self.vault_path)
        return result_data

    def push_changes(self, message: Optional[str] = None) -> dict:
        """
        Commit pending changes and push to remote.

        Args:
            message: Custom commit message. Default: "{agent_id}: auto-sync"

        Returns:
            Dict with success, commit_hash, files_committed, conflict
        """
        result_data = {
            "success": False,
            "timestamp": datetime.utcnow().isoformat(),
            "commit_hash": "",
            "files_committed": [],
            "conflict": False,
        }

        try:
            # Check for changes
            status_result = self._run_git("status", "--porcelain")
            if not status_result.stdout.strip():
                result_data["success"] = True
                result_data["commit_hash"] = self._get_head_hash()
                logger.debug("No changes to push")
                return result_data

            # Stage all changes
            self._run_git("add", "-A")

            # Get list of staged files
            diff_result = self._run_git("diff", "--cached", "--name-only")
            result_data["files_committed"] = [
                f.strip() for f in diff_result.stdout.strip().split("\n") if f.strip()
            ]

            # Commit
            commit_msg = message or f"{self.agent_id}: auto-sync"
            commit_result = self._run_git("commit", "-m", commit_msg, check=False)

            if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stdout:
                self.state.record_failure(commit_result.stderr.strip())
                self.state.save(self.vault_path)
                return result_data

            # Push
            push_result = self._run_git("push", self.remote, self.branch, check=False)

            if push_result.returncode == 0:
                result_data["success"] = True
                result_data["commit_hash"] = self._get_head_hash()
                self.state.record_push(
                    result_data["commit_hash"],
                    files_added=len(result_data["files_committed"]),
                )
                logger.info(
                    f"Push successful: {len(result_data['files_committed'])} files "
                    f"({result_data['commit_hash'][:8]})"
                )
            elif "rejected" in push_result.stderr or "conflict" in push_result.stderr.lower():
                result_data["conflict"] = True
                self.state.record_failure("push rejected (conflict)")
                logger.warning("Push rejected - remote has changes")
            else:
                self.state.record_failure(push_result.stderr.strip())
                logger.error(f"Push failed: {push_result.stderr.strip()}")

        except SyncError as e:
            self.state.record_failure(str(e))
            logger.error(f"Push error: {e}")

        self.state.save(self.vault_path)
        return result_data

    def sync(self, message: Optional[str] = None) -> dict:
        """
        Full sync cycle: pull then push.

        Args:
            message: Commit message for push

        Returns:
            Combined result dict
        """
        pull_result = self.pull_changes()
        push_result = self.push_changes(message=message)

        return {
            "pull": pull_result,
            "push": push_result,
            "success": pull_result["success"] and push_result["success"],
        }

    def write_sync_state(self) -> Path:
        """Write current sync state to Health/sync_state.json."""
        return self.state.save(self.vault_path)
