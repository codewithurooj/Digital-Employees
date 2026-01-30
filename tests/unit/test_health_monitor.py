"""Unit tests for health monitor (T067)."""

import pytest


class TestHealthMonitor:
    """Tests for the HealthMonitor class."""

    def test_check_resources(self, tmp_path):
        from src.cloud.health_monitor import HealthMonitor

        monitor = HealthMonitor(vault_path=str(tmp_path))
        resources = monitor.check_resources()
        assert "cpu_percent" in resources
        assert "memory_percent" in resources
        assert "disk_percent" in resources
        assert 0 <= resources["cpu_percent"] <= 100
        assert 0 <= resources["memory_percent"] <= 100

    def test_evaluate_status_healthy(self, tmp_path):
        from src.cloud.health_monitor import HealthMonitor

        monitor = HealthMonitor(vault_path=str(tmp_path))
        status = monitor.evaluate_status({
            "cpu_percent": 30,
            "memory_percent": 40,
            "disk_percent": 50,
        })
        assert status == "healthy"

    def test_evaluate_status_warning(self, tmp_path):
        from src.cloud.health_monitor import HealthMonitor

        monitor = HealthMonitor(vault_path=str(tmp_path))
        status = monitor.evaluate_status({
            "cpu_percent": 75,
            "memory_percent": 85,
            "disk_percent": 50,
        })
        assert status == "warning"

    def test_evaluate_status_critical(self, tmp_path):
        from src.cloud.health_monitor import HealthMonitor

        monitor = HealthMonitor(vault_path=str(tmp_path))
        status = monitor.evaluate_status({
            "cpu_percent": 95,
            "memory_percent": 97,
            "disk_percent": 50,
        })
        assert status == "critical"

    def test_write_status_md(self, tmp_path):
        from src.cloud.health_monitor import HealthMonitor

        monitor = HealthMonitor(vault_path=str(tmp_path))
        monitor.write_status()
        status_file = tmp_path / "Health" / "status.md"
        assert status_file.exists()
        content = status_file.read_text()
        assert "Health Status" in content

    def test_log_incident(self, tmp_path):
        from src.cloud.health_monitor import HealthMonitor

        monitor = HealthMonitor(vault_path=str(tmp_path))
        monitor.log_incident("test_process", "Process crashed", severity="critical")
        log_files = list((tmp_path / "Logs").glob("*.jsonl"))
        assert len(log_files) >= 1
