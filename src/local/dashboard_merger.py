"""
Dashboard Merger - Merges cloud-written Updates into Dashboard.md.

Single-writer rule: Only the local agent writes to Dashboard.md.
Cloud agent writes to /Updates/ folder, and the local agent merges
those updates into the Dashboard.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.models.update_file import UpdateFile, MergeStatus

logger = logging.getLogger(__name__)


class DashboardMerger:
    """Merges cloud Updates files into Dashboard.md (local-only)."""

    def __init__(self, vault_path: Path):
        self.vault_path = Path(vault_path)
        self.dashboard_path = self.vault_path / "Dashboard.md"
        self.updates_dir = self.vault_path / "Updates"

    def get_pending_updates(self) -> list[Path]:
        """Find all unmerged update files."""
        if not self.updates_dir.exists():
            return []

        pending = []
        for filepath in sorted(self.updates_dir.glob("*.md")):
            content = filepath.read_text(encoding="utf-8")
            if "merge_status: pending" in content:
                pending.append(filepath)

        return pending

    def merge_update(self, update_path: Path) -> bool:
        """
        Merge a single update file into Dashboard.md.

        Args:
            update_path: Path to the update file

        Returns:
            True if merge was successful
        """
        try:
            update_content = update_path.read_text(encoding="utf-8")

            # Extract the content body (after frontmatter)
            body = self._extract_body(update_content)
            if not body.strip():
                logger.warning(f"Empty update body: {update_path.name}")
                self._mark_status(update_path, "skipped")
                return False

            # Read current dashboard
            if self.dashboard_path.exists():
                dashboard_content = self.dashboard_path.read_text(encoding="utf-8")
            else:
                dashboard_content = "# Dashboard\n\n"

            # Append update to dashboard
            merge_section = (
                f"\n\n---\n\n"
                f"## Update: {update_path.stem}\n"
                f"*Merged at {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
                f"{body}\n"
            )

            dashboard_content += merge_section
            self.dashboard_path.write_text(dashboard_content, encoding="utf-8")

            # Mark update as merged
            self._mark_status(update_path, "merged")

            logger.info(f"Merged update: {update_path.name} into Dashboard.md")
            return True

        except Exception as e:
            logger.error(f"Failed to merge update {update_path.name}: {e}")
            return False

    def merge_all_pending(self) -> int:
        """
        Merge all pending updates into Dashboard.md.

        Returns:
            Number of updates successfully merged
        """
        pending = self.get_pending_updates()
        if not pending:
            return 0

        merged = 0
        for update_path in pending:
            if self.merge_update(update_path):
                merged += 1

        logger.info(f"Merged {merged}/{len(pending)} pending updates")
        return merged

    def cleanup_old_updates(self, days: int = 7) -> int:
        """Remove merged/skipped update files older than N days."""
        if not self.updates_dir.exists():
            return 0

        import time
        cutoff = time.time() - (days * 86400)
        removed = 0

        for filepath in self.updates_dir.glob("*.md"):
            content = filepath.read_text(encoding="utf-8")
            if ("merge_status: merged" in content or "merge_status: skipped" in content):
                if filepath.stat().st_mtime < cutoff:
                    filepath.unlink()
                    removed += 1

        return removed

    def _extract_body(self, content: str) -> str:
        """Extract content body after YAML frontmatter."""
        if content.startswith("---"):
            # Find the closing ---
            end = content.find("---", 3)
            if end != -1:
                body = content[end + 3:].strip()
                # Remove trailing merge instruction
                if body.endswith("*"):
                    lines = body.split("\n")
                    while lines and lines[-1].startswith("*Merge"):
                        lines.pop()
                    body = "\n".join(lines).strip()
                return body
        return content

    def _mark_status(self, filepath: Path, status: str) -> None:
        """Update the merge_status in a file's frontmatter."""
        content = filepath.read_text(encoding="utf-8")
        updated = re.sub(
            r"merge_status:\s*\w+",
            f"merge_status: {status}",
            content,
        )
        filepath.write_text(updated, encoding="utf-8")
