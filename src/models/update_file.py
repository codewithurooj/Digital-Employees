"""UpdateFile model for cloud-written updates to be merged by local agent."""

from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class UpdateType(str, Enum):
    """Type of update file."""
    EMAIL_SUMMARY = "email_summary"
    TASK_SUMMARY = "task_summary"
    ALERT = "alert"


class MergeStatus(str, Enum):
    """Merge status of the update."""
    PENDING = "pending"
    MERGED = "merged"
    SKIPPED = "skipped"


class UpdateFile(BaseModel):
    """Cloud-written updates for local Dashboard merging."""

    update_type: UpdateType
    update_date: date = Field(default_factory=date.today)
    generated_by: str = Field(default="cloud")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    merge_status: MergeStatus = Field(default=MergeStatus.PENDING)
    merge_target: str = Field(default="Dashboard.md")
    content: str = Field(default="", description="Markdown content of the update")

    def mark_merged(self) -> None:
        """Mark the update as merged into Dashboard."""
        self.merge_status = MergeStatus.MERGED

    def mark_skipped(self) -> None:
        """Mark the update as skipped."""
        self.merge_status = MergeStatus.SKIPPED

    @property
    def filename(self) -> str:
        """Generate filename for this update."""
        return f"{self.update_type.value}_{self.update_date.isoformat()}.md"

    def to_markdown(self) -> str:
        """Generate markdown file content with frontmatter."""
        return f"""---
type: update
update_type: {self.update_type.value}
date: {self.update_date.isoformat()}
generated_by: {self.generated_by}
generated_at: {self.generated_at.isoformat()}
merge_status: {self.merge_status.value}
merge_target: {self.merge_target}
---

{self.content}

---
*Merge this into {self.merge_target} when local comes online*
"""

    def save(self, vault_path: Path) -> Path:
        """Save update file to vault Updates folder."""
        updates_dir = vault_path / "Updates"
        updates_dir.mkdir(parents=True, exist_ok=True)
        filepath = updates_dir / self.filename
        filepath.write_text(self.to_markdown(), encoding="utf-8")
        return filepath

    @classmethod
    def find_pending(cls, vault_path: Path) -> list[Path]:
        """Find all pending update files in the vault."""
        updates_dir = vault_path / "Updates"
        if not updates_dir.exists():
            return []
        return sorted(updates_dir.glob("*.md"))
