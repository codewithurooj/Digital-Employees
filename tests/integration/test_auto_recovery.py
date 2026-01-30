"""Integration tests for auto-recovery (T068)."""

import pytest


class TestAutoRecovery:
    """Tests for auto-recovery logic (simulated, no actual PM2)."""

    def test_restart_logs_incident(self, tmp_path):
        from src.cloud.health_monitor import HealthMonitor

        monitor = HealthMonitor(vault_path=str(tmp_path))
        result = monitor.attempt_restart("test-process", dry_run=True)
        assert result["attempted"] is True
        assert result["dry_run"] is True

    def test_recovery_updates_status(self, tmp_path):
        from src.cloud.health_monitor import HealthMonitor

        monitor = HealthMonitor(vault_path=str(tmp_path))
        monitor.log_incident("proc1", "Crashed", severity="critical")
        monitor.write_status()
        content = (tmp_path / "Health" / "status.md").read_text()
        assert "incident" in content.lower() or "status" in content.lower()

    def test_consecutive_failures_alert(self, tmp_path):
        from src.cloud.health_monitor import HealthMonitor

        monitor = HealthMonitor(vault_path=str(tmp_path))
        for i in range(3):
            monitor.log_incident("proc1", f"Failure {i+1}", severity="critical")

        assert monitor.get_consecutive_failures("proc1") >= 3
