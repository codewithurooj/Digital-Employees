"""HealthStatus model for cloud agent health monitoring."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class OverallStatus(str, Enum):
    """Overall health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class ProcessInfo(BaseModel):
    """Status of a managed process."""
    name: str
    status: str = Field(default="unknown")  # running, stopped, errored, restarting
    pid: Optional[int] = None
    uptime_seconds: int = Field(default=0, ge=0)
    restarts_today: int = Field(default=0, ge=0)
    memory_mb: float = Field(default=0, ge=0)
    cpu_percent: float = Field(default=0, ge=0)


class ApiInfo(BaseModel):
    """Status of an API connection."""
    service: str
    connected: bool = False
    last_successful: Optional[datetime] = None
    latency_ms: int = Field(default=0, ge=0)
    errors_1h: int = Field(default=0, ge=0)
    error_message: Optional[str] = None


class ResourceMetrics(BaseModel):
    """System resource usage metrics."""
    cpu_percent: float = Field(default=0, ge=0, le=100)
    memory_percent: float = Field(default=0, ge=0, le=100)
    disk_percent: float = Field(default=0, ge=0, le=100)
    memory_used_mb: int = Field(default=0, ge=0)
    memory_total_mb: int = Field(default=0, ge=0)
    disk_used_gb: float = Field(default=0, ge=0)
    disk_total_gb: float = Field(default=0, ge=0)


class Thresholds(BaseModel):
    """Monitoring thresholds for alerts."""
    cpu_warning: int = 70
    cpu_critical: int = 90
    memory_warning: int = 80
    memory_critical: int = 95
    disk_warning: int = 85
    disk_critical: int = 95
    api_error_threshold: int = 5
    process_restart_max: int = 10


class Incident(BaseModel):
    """Record of a health incident."""
    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: str  # process_crash, api_failure, resource_critical, sync_failure
    severity: str = "warning"  # warning, error, critical
    component: str = ""
    message: str = ""
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None


class HealthStatus(BaseModel):
    """Records cloud agent health metrics and incidents."""

    agent_id: str = Field(default="cloud")
    last_check: datetime = Field(default_factory=datetime.utcnow)
    overall_status: OverallStatus = Field(default=OverallStatus.HEALTHY)
    check_interval: int = Field(default=60)

    processes: list[ProcessInfo] = Field(default_factory=list)
    apis: list[ApiInfo] = Field(default_factory=list)
    resources: ResourceMetrics = Field(default_factory=ResourceMetrics)
    thresholds: Thresholds = Field(default_factory=Thresholds)

    incidents_today: list[Incident] = Field(default_factory=list)
    last_incident: Optional[Incident] = None
    uptime_percent_30d: float = Field(default=100.0, ge=0, le=100)

    def compute_overall_status(self) -> OverallStatus:
        """Calculate overall status from component statuses."""
        # Check for critical conditions
        for proc in self.processes:
            if proc.status in ("stopped", "errored"):
                return OverallStatus.CRITICAL

        for api in self.apis:
            if not api.connected and api.errors_1h >= self.thresholds.api_error_threshold:
                return OverallStatus.CRITICAL

        if self.resources.cpu_percent >= self.thresholds.cpu_critical:
            return OverallStatus.CRITICAL
        if self.resources.memory_percent >= self.thresholds.memory_critical:
            return OverallStatus.CRITICAL
        if self.resources.disk_percent >= self.thresholds.disk_critical:
            return OverallStatus.CRITICAL

        # Check for warning conditions
        for api in self.apis:
            if not api.connected:
                return OverallStatus.DEGRADED

        if self.resources.cpu_percent >= self.thresholds.cpu_warning:
            return OverallStatus.DEGRADED
        if self.resources.memory_percent >= self.thresholds.memory_warning:
            return OverallStatus.DEGRADED
        if self.resources.disk_percent >= self.thresholds.disk_warning:
            return OverallStatus.DEGRADED

        return OverallStatus.HEALTHY

    def add_incident(self, incident: Incident) -> None:
        """Record a new incident."""
        self.incidents_today.append(incident)
        self.last_incident = incident

    def to_markdown(self) -> str:
        """Generate Health/status.md content."""
        status_emoji = {
            OverallStatus.HEALTHY: "🟢",
            OverallStatus.DEGRADED: "🟡",
            OverallStatus.CRITICAL: "🔴",
        }

        proc_rows = "\n".join([
            f"| {p.name} | {'🟢' if p.status == 'running' else '🔴'} {p.status.title()} | "
            f"{p.uptime_seconds // 3600}h {(p.uptime_seconds % 3600) // 60}m | "
            f"{p.memory_mb:.0f} MB | {p.cpu_percent:.1f}% |"
            for p in self.processes
        ]) or "| No processes | - | - | - | - |"

        api_rows = "\n".join([
            f"| {a.service} | {'🟢' if a.connected else '🔴'} "
            f"{'Connected' if a.connected else 'Error'} | "
            f"{a.latency_ms}ms | {a.errors_1h} |"
            for a in self.apis
        ]) or "| No APIs | - | - | - |"

        incidents_text = "\n".join([
            f"- [{i.severity.upper()}] {i.timestamp.strftime('%H:%M')} - {i.message}"
            for i in self.incidents_today
        ]) or "None in the last 24 hours."

        return f"""---
type: health_status
agent_id: {self.agent_id}
last_check: {self.last_check.isoformat()}
overall_status: {self.overall_status.value}
check_interval: {self.check_interval}
---

# Cloud Agent Health Status

> Last Check: {self.last_check.strftime('%Y-%m-%d %I:%M %p')}

## Overall Status: {status_emoji.get(self.overall_status, '❓')} {self.overall_status.value.title()}

## Processes

| Process | Status | Uptime | Memory | CPU |
|---------|--------|--------|--------|-----|
{proc_rows}

## API Connectivity

| Service | Status | Latency | Errors (1h) |
|---------|--------|---------|-------------|
{api_rows}

## Resources

| Metric | Current | Warning | Critical |
|--------|---------|---------|----------|
| CPU | {self.resources.cpu_percent:.0f}% | {self.thresholds.cpu_warning}% | {self.thresholds.cpu_critical}% |
| Memory | {self.resources.memory_percent:.0f}% | {self.thresholds.memory_warning}% | {self.thresholds.memory_critical}% |
| Disk | {self.resources.disk_percent:.0f}% | {self.thresholds.disk_warning}% | {self.thresholds.disk_critical}% |

## Recent Incidents

{incidents_text}

## Uptime

- 30-day uptime: {self.uptime_percent_30d:.1f}%

---
*Auto-generated by Health Monitor*
"""

    def save(self, vault_path: Path) -> Path:
        """Save health status to vault."""
        status_file = vault_path / "Health" / "status.md"
        status_file.parent.mkdir(parents=True, exist_ok=True)
        status_file.write_text(self.to_markdown(), encoding="utf-8")
        return status_file
