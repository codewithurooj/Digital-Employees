"""Unit tests for local orchestrator (T079)."""

import pytest
from pathlib import Path


class TestLocalOrchestrator:
    """Tests for the LocalOrchestrator class."""

    def test_init_sets_agent_id(self, tmp_path):
        from src.local.local_orchestrator import LocalOrchestrator

        (tmp_path / "Logs").mkdir()

        orch = LocalOrchestrator(vault_path=str(tmp_path), dry_run=True)
        assert orch.agent_id == "local"

    def test_init_creates_components(self, tmp_path):
        from src.local.local_orchestrator import LocalOrchestrator

        (tmp_path / "Logs").mkdir()

        orch = LocalOrchestrator(vault_path=str(tmp_path), dry_run=True)
        assert orch.sync_puller is not None
        assert orch.dashboard_merger is not None

    def test_extract_frontmatter(self, tmp_path):
        from src.local.local_orchestrator import LocalOrchestrator

        (tmp_path / "Logs").mkdir()

        orch = LocalOrchestrator(vault_path=str(tmp_path), dry_run=True)
        content = """---
action: send_email
domain: email
---

# Approval
"""
        assert orch._extract_frontmatter(content, "action") == "send_email"
        assert orch._extract_frontmatter(content, "domain") == "email"

    def test_process_approved_actions_dry_run(self, tmp_path):
        from src.local.local_orchestrator import LocalOrchestrator

        (tmp_path / "Logs").mkdir()
        (tmp_path / "Approved").mkdir()

        # Create a test approved action
        approved = tmp_path / "Approved" / "test_action.md"
        approved.write_text("""---
action: send_email
domain: email
---
# Test
""")

        orch = LocalOrchestrator(vault_path=str(tmp_path), dry_run=True)
        orch.is_running = True
        orch._process_approved_actions()

        # In dry_run, file should NOT be moved
        assert approved.exists()

    def test_start_and_stop(self, tmp_path):
        from src.local.local_orchestrator import LocalOrchestrator

        (tmp_path / "Logs").mkdir()

        orch = LocalOrchestrator(vault_path=str(tmp_path), dry_run=True)
        orch.start()
        assert orch.is_running is True
        orch.stop()
        assert orch.is_running is False

    def test_mark_consumed(self, tmp_path):
        from src.local.local_orchestrator import LocalOrchestrator

        (tmp_path / "Logs").mkdir()

        orch = LocalOrchestrator(vault_path=str(tmp_path), dry_run=True)

        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n")
        orch._mark_consumed(test_file)

        content = test_file.read_text()
        assert "Consumed at:" in content
