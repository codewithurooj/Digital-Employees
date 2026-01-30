"""Unit tests for cloud orchestrator (T078)."""

import pytest
from pathlib import Path


class TestCloudOrchestrator:
    """Tests for the CloudOrchestrator class."""

    def test_init_sets_cloud_zone(self, tmp_path):
        from src.cloud.cloud_orchestrator import CloudOrchestrator
        from src.cloud.work_zone import WorkZone

        # Create required vault structure
        (tmp_path / "Logs").mkdir()
        (tmp_path / "Health").mkdir()

        orch = CloudOrchestrator(vault_path=str(tmp_path), dry_run=True)
        assert orch.agent_zone == WorkZone.CLOUD

    def test_init_creates_skills(self, tmp_path):
        from src.cloud.cloud_orchestrator import CloudOrchestrator

        (tmp_path / "Logs").mkdir()
        (tmp_path / "Health").mkdir()

        orch = CloudOrchestrator(vault_path=str(tmp_path), dry_run=True)
        assert orch.email_triage is not None
        assert orch.social_draft is not None
        assert orch.cloud_odoo is not None

    def test_load_watchers_returns_list(self, tmp_path):
        from src.cloud.cloud_orchestrator import CloudOrchestrator

        (tmp_path / "Logs").mkdir()
        (tmp_path / "Health").mkdir()
        (tmp_path / "Drop").mkdir()

        orch = CloudOrchestrator(vault_path=str(tmp_path), dry_run=True)
        watchers = orch._load_watchers()
        assert isinstance(watchers, list)
        assert "filesystem" in watchers

    def test_parse_action_file(self, tmp_path):
        from src.cloud.cloud_orchestrator import CloudOrchestrator

        (tmp_path / "Logs").mkdir()
        (tmp_path / "Health").mkdir()

        orch = CloudOrchestrator(vault_path=str(tmp_path), dry_run=True)

        content = """---
from: "client@example.com"
subject: "Project update"
---

## Body

Hello, please send me an update on the project.
"""
        result = orch._parse_action_file(content, Path("test_email.md"))
        assert result is not None
        assert result["from"] == "client@example.com"
        assert result["subject"] == "Project update"

    def test_parse_action_file_returns_none_for_empty(self, tmp_path):
        from src.cloud.cloud_orchestrator import CloudOrchestrator

        (tmp_path / "Logs").mkdir()
        (tmp_path / "Health").mkdir()

        orch = CloudOrchestrator(vault_path=str(tmp_path), dry_run=True)
        result = orch._parse_action_file("no frontmatter here", Path("test.md"))
        assert result is None

    def test_start_and_stop(self, tmp_path):
        from src.cloud.cloud_orchestrator import CloudOrchestrator

        (tmp_path / "Logs").mkdir()
        (tmp_path / "Health").mkdir()

        orch = CloudOrchestrator(vault_path=str(tmp_path), dry_run=True)
        orch.start()
        assert orch.is_running is True
        orch.stop()
        assert orch.is_running is False

    def test_dry_run_sync_after_task(self, tmp_path):
        from src.cloud.cloud_orchestrator import CloudOrchestrator

        (tmp_path / "Logs").mkdir()
        (tmp_path / "Health").mkdir()

        orch = CloudOrchestrator(vault_path=str(tmp_path), dry_run=True)
        # Should not raise in dry_run mode
        orch.sync_after_task()
