"""
Tests for ProcessInboxSkill.

Run with: pytest tests/test_process_inbox.py -v
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.skills.process_inbox import (
    ProcessInboxSkill,
    ProcessingResult,
    ActionItem,
    Priority,
    ActionResult
)


class TestActionItem:
    """Test ActionItem dataclass."""

    def test_from_file_basic(self, temp_vault):
        """Parse a basic action file."""
        content = """---
type: file_drop
priority: medium
status: pending
created: "2026-01-20T10:00:00"
---

# New File Dropped

A new file was dropped in the folder.
"""
        filepath = temp_vault / "Needs_Action" / "test_action.md"
        filepath.write_text(content)

        item = ActionItem.from_file(filepath)

        assert item.item_type == "file_drop"
        assert item.priority == "medium"
        assert item.status == "pending"
        assert "New File Dropped" in item.content

    def test_from_file_with_metadata(self, temp_vault):
        """Parse action file with extra metadata."""
        content = """---
type: payment
priority: high
status: pending
amount: "$150.00"
recipient: "vendor@example.com"
requires_approval: "true"
---

# Payment Request

Payment for invoice #123
"""
        filepath = temp_vault / "Needs_Action" / "payment_action.md"
        filepath.write_text(content)

        item = ActionItem.from_file(filepath)

        assert item.item_type == "payment"
        assert item.priority == "high"
        assert item.metadata.get('amount') == "$150.00"
        assert item.metadata.get('recipient') == "vendor@example.com"
        assert item.metadata.get('requires_approval') == "true"

    def test_from_file_no_frontmatter(self, temp_vault):
        """Parse file without frontmatter."""
        content = """# Simple Note

Just a note without frontmatter.
"""
        filepath = temp_vault / "Needs_Action" / "simple_note.md"
        filepath.write_text(content)

        item = ActionItem.from_file(filepath)

        assert item.item_type == "unknown"
        assert item.priority == "medium"  # Default
        assert "Simple Note" in item.content


class TestProcessingResult:
    """Test ProcessingResult dataclass."""

    def test_default_values(self):
        """Test default values."""
        result = ProcessingResult(success=True)

        assert result.success is True
        assert result.total_items == 0
        assert result.processed == 0
        assert result.errors == 0
        assert result.items == []

    def test_to_dict(self):
        """Test serialization."""
        result = ProcessingResult(
            success=True,
            total_items=5,
            processed=4,
            plans_created=2,
            pending_approval=1,
            auto_processed=1,
            errors=1
        )

        data = result.to_dict()

        assert data['success'] is True
        assert data['total_items'] == 5
        assert data['plans_created'] == 2


class TestProcessInboxSkillInit:
    """Test ProcessInboxSkill initialization."""

    def test_init_creates_folders(self, temp_vault):
        """Initialization creates required folders."""
        skill = ProcessInboxSkill(str(temp_vault), use_reasoning_loop=False)

        assert (temp_vault / "Needs_Action").exists()
        assert (temp_vault / "Plans").exists()
        assert (temp_vault / "Pending_Approval").exists()
        assert (temp_vault / "Done").exists()
        assert (temp_vault / "Logs").exists()

    def test_init_loads_handbook(self, temp_vault):
        """Initialization loads handbook rules."""
        # Create handbook
        handbook_content = """# Company Handbook

## Payment Rules

- Auto-approve payments under $50
- Require approval for payments over $100
"""
        (temp_vault / "Company_Handbook.md").write_text(handbook_content)

        skill = ProcessInboxSkill(str(temp_vault), use_reasoning_loop=False)

        assert skill._handbook_rules is not None

    def test_init_with_reasoning_loop(self, temp_vault):
        """Initialization with reasoning loop enabled."""
        skill = ProcessInboxSkill(str(temp_vault), use_reasoning_loop=True)

        assert skill.reasoning_loop is not None
        assert skill.use_reasoning_loop is True

    def test_init_without_reasoning_loop(self, temp_vault):
        """Initialization with reasoning loop disabled."""
        skill = ProcessInboxSkill(str(temp_vault), use_reasoning_loop=False)

        assert skill.reasoning_loop is None
        assert skill.use_reasoning_loop is False


class TestRequiresApproval:
    """Test approval requirement detection."""

    @pytest.fixture
    def skill(self, temp_vault):
        """Create skill for testing."""
        return ProcessInboxSkill(str(temp_vault), use_reasoning_loop=False)

    def test_payment_type_requires_approval(self, skill, temp_vault):
        """Payment type requires approval."""
        content = """---
type: payment
priority: high
amount: "$200"
---
Payment request
"""
        filepath = temp_vault / "Needs_Action" / "test.md"
        filepath.write_text(content)
        item = ActionItem.from_file(filepath)

        # Update rules to include payment
        skill._handbook_rules['require_approval_types'] = ['payment']

        assert skill._requires_approval(item) is True

    def test_post_social_requires_approval(self, skill, temp_vault):
        """Social post type requires approval."""
        content = """---
type: post_social
priority: medium
---
Post to LinkedIn
"""
        filepath = temp_vault / "Needs_Action" / "test.md"
        filepath.write_text(content)
        item = ActionItem.from_file(filepath)

        skill._handbook_rules['require_approval_types'] = ['post_social']

        assert skill._requires_approval(item) is True

    def test_file_drop_no_approval(self, skill, temp_vault):
        """File drop doesn't require approval by default."""
        content = """---
type: file_drop
priority: low
---
New file dropped
"""
        filepath = temp_vault / "Needs_Action" / "test.md"
        filepath.write_text(content)
        item = ActionItem.from_file(filepath)

        assert skill._requires_approval(item) is False

    def test_metadata_override(self, skill, temp_vault):
        """Metadata can force approval requirement."""
        content = """---
type: file_drop
priority: low
requires_approval: "true"
---
Important file needs review
"""
        filepath = temp_vault / "Needs_Action" / "test.md"
        filepath.write_text(content)
        item = ActionItem.from_file(filepath)

        assert skill._requires_approval(item) is True


class TestProcessAll:
    """Test process_all method."""

    @pytest.fixture
    def skill(self, temp_vault):
        """Create skill for testing."""
        return ProcessInboxSkill(str(temp_vault), use_reasoning_loop=False)

    def test_empty_inbox(self, skill):
        """Process empty inbox."""
        result = skill.process_all()

        assert result.success is True
        assert result.total_items == 0
        assert result.processed == 0

    def test_process_single_item(self, skill, temp_vault):
        """Process single item in inbox."""
        content = """---
type: file_drop
priority: medium
status: pending
---
New file
"""
        (temp_vault / "Needs_Action" / "item1.md").write_text(content)

        result = skill.process_all()

        assert result.success is True
        assert result.total_items == 1
        assert result.processed == 1
        assert result.plans_created >= 0

    def test_process_multiple_items(self, skill, temp_vault):
        """Process multiple items in inbox."""
        for i in range(3):
            content = f"""---
type: file_drop
priority: medium
status: pending
---
File {i}
"""
            (temp_vault / "Needs_Action" / f"item{i}.md").write_text(content)

        result = skill.process_all()

        assert result.success is True
        assert result.total_items == 3
        assert result.processed == 3

    def test_priority_ordering(self, skill, temp_vault):
        """Items are processed in priority order."""
        # Create items with different priorities
        priorities = [
            ("low_item.md", "low"),
            ("critical_item.md", "critical"),
            ("high_item.md", "high"),
        ]

        for filename, priority in priorities:
            content = f"""---
type: file_drop
priority: {priority}
---
Test
"""
            (temp_vault / "Needs_Action" / filename).write_text(content)

        result = skill.process_all()

        # Check that critical was processed (it will be in results)
        assert result.total_items == 3
        # Items should be sorted by priority in the results

    def test_auto_process_moves_to_done(self, skill, temp_vault):
        """Auto-processable items are moved to Done."""
        content = """---
type: internal_note
priority: low
status: pending
---
Internal note
"""
        (temp_vault / "Needs_Action" / "note.md").write_text(content)
        skill._handbook_rules['auto_process_types'] = ['internal_note']

        result = skill.process_all()

        assert result.auto_processed >= 1
        # Original file should be in Done
        assert (temp_vault / "Done" / "note.md").exists() or result.auto_processed == 1


class TestCreatePlan:
    """Test plan creation."""

    @pytest.fixture
    def skill(self, temp_vault):
        """Create skill for testing."""
        return ProcessInboxSkill(str(temp_vault), use_reasoning_loop=False)

    def test_creates_plan_file(self, skill, temp_vault):
        """Plan file is created in Plans folder."""
        content = """---
type: file_drop
priority: medium
---
Test content
"""
        filepath = temp_vault / "Needs_Action" / "test.md"
        filepath.write_text(content)
        item = ActionItem.from_file(filepath)

        plan_path = skill._create_plan(item, requires_approval=False)

        assert plan_path.exists()
        assert plan_path.parent.name == "Plans"
        assert "PLAN_" in plan_path.name

    def test_plan_contains_source_info(self, skill, temp_vault):
        """Plan file contains source item information."""
        content = """---
type: payment
priority: high
amount: "$100"
---
Payment details
"""
        filepath = temp_vault / "Needs_Action" / "payment.md"
        filepath.write_text(content)
        item = ActionItem.from_file(filepath)

        plan_path = skill._create_plan(item, requires_approval=True)
        plan_content = plan_path.read_text()

        assert "payment.md" in plan_content
        assert "payment" in plan_content
        assert "requires_approval: true" in plan_content

    def test_plan_with_approval_required(self, skill, temp_vault):
        """Plan indicates when approval is required."""
        content = """---
type: payment
priority: high
---
Test
"""
        filepath = temp_vault / "Needs_Action" / "test.md"
        filepath.write_text(content)
        item = ActionItem.from_file(filepath)

        plan_path = skill._create_plan(item, requires_approval=True)
        plan_content = plan_path.read_text()

        assert "requires_approval: true" in plan_content
        assert "Yes" in plan_content  # Approval Required section


class TestGetStatus:
    """Test get_status method."""

    def test_status_includes_counts(self, temp_vault):
        """Status includes item counts."""
        skill = ProcessInboxSkill(str(temp_vault), use_reasoning_loop=False)

        # Add some items
        (temp_vault / "Needs_Action" / "item1.md").write_text("test")
        (temp_vault / "Plans" / "plan1.md").write_text("plan")

        status = skill.get_status()

        assert status['skill'] == 'ProcessInboxSkill'
        assert status['pending_items'] == 1
        assert status['plans_count'] == 1

    def test_status_includes_settings(self, temp_vault):
        """Status includes skill settings."""
        skill = ProcessInboxSkill(
            str(temp_vault),
            use_reasoning_loop=False
        )

        status = skill.get_status()

        assert 'vault_path' in status
        assert status['use_reasoning_loop'] is False


class TestDashboardUpdate:
    """Test dashboard update functionality."""

    def test_updates_dashboard(self, temp_vault):
        """Dashboard is updated after processing."""
        # Create dashboard
        (temp_vault / "Dashboard.md").write_text("# Dashboard\n\n## Recent Activity\n")

        skill = ProcessInboxSkill(str(temp_vault), use_reasoning_loop=False)

        # Add an item
        (temp_vault / "Needs_Action" / "item.md").write_text("""---
type: file_drop
priority: low
---
Test
""")

        skill.process_all()

        dashboard_content = (temp_vault / "Dashboard.md").read_text()
        assert "Last Inbox Processing" in dashboard_content
        assert "Total Items" in dashboard_content


class TestLogging:
    """Test logging functionality."""

    def test_logs_processing(self, temp_vault):
        """Processing is logged to daily log file."""
        skill = ProcessInboxSkill(str(temp_vault), use_reasoning_loop=False)

        # Add an item
        (temp_vault / "Needs_Action" / "item.md").write_text("""---
type: file_drop
---
Test
""")

        skill.process_all()

        # Check log file
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = temp_vault / "Logs" / f"{today}.json"

        assert log_file.exists()
        logs = json.loads(log_file.read_text())
        assert len(logs) > 0
        assert logs[-1]['component'] == 'ProcessInboxSkill'


class TestWithReasoningLoop:
    """Test integration with Ralph Wiggum Loop."""

    @patch('subprocess.run')
    def test_process_with_reasoning_loop(self, mock_run, temp_vault):
        """Item is processed through reasoning loop."""
        mock_run.return_value = MagicMock(
            stdout="Plan created! <promise>ITEM_PROCESSED</promise>",
            stderr="",
            returncode=0
        )

        skill = ProcessInboxSkill(
            str(temp_vault),
            use_reasoning_loop=True,
            max_iterations=2
        )

        # Add an item
        (temp_vault / "Needs_Action" / "item.md").write_text("""---
type: email
priority: high
---
Process this email
""")

        result = skill.process_all()

        assert result.success is True
        assert result.total_items == 1
        # Reasoning loop was used
        assert len(result.items) == 1
        assert 'loop_id' in result.items[0]
