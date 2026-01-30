"""
Audit Logger - Structured JSONL audit logging with rotation and retention.

Provides comprehensive audit logging for all AI Employee actions
with support for daily rotation and 90-day retention.

Usage:
    from src.utils.audit_logger import AuditLogger

    logger = AuditLogger(vault_path='./AI_Employee_Vault')

    # Log an action
    logger.log_action(
        action_type='email_sent',
        component='email_mcp',
        actor='orchestrator',
        target='client@example.com',
        parameters={'subject': 'Hello'},
        result='success',
    )

    # Query logs
    entries = logger.query_logs(
        start_date='2026-01-20',
        end_date='2026-01-25',
        action_type='email_sent',
    )

Features:
- JSONL format (one JSON object per line)
- Daily rotation: Logs/YYYY-MM-DD.jsonl
- 90-day retention with automatic cleanup
- Structured fields for queryability
- Concurrent-write safe (append-only)
"""

import json
import logging
import os
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Optional


class AuditEntry:
    """Structured audit log entry."""

    def __init__(
        self,
        action_type: str,
        component: str,
        actor: str,
        target: Optional[str] = None,
        parameters: Optional[dict[str, Any]] = None,
        approval_status: Optional[str] = None,
        approval_id: Optional[str] = None,
        result: str = "pending",
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ):
        """
        Create an audit entry.

        Args:
            action_type: Type of action (e.g., 'email_sent', 'invoice_synced')
            component: System component (e.g., 'email_mcp', 'odoo_watcher')
            actor: Who/what initiated the action (e.g., 'orchestrator', 'user')
            target: Target of the action (e.g., email address, file path)
            parameters: Action parameters (sanitized, no secrets)
            approval_status: HITL approval status if applicable
            approval_id: Approval ID if applicable
            result: Action result ('success', 'failure', 'pending')
            error: Error message if result is 'failure'
            duration_ms: Action duration in milliseconds
        """
        self.timestamp = datetime.utcnow()
        self.action_type = action_type
        self.component = component
        self.actor = actor
        self.target = target
        self.parameters = parameters or {}
        self.approval_status = approval_status
        self.approval_id = approval_id
        self.result = result
        self.error = error
        self.duration_ms = duration_ms

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary."""
        entry = {
            "timestamp": self.timestamp.isoformat() + "Z",
            "action_type": self.action_type,
            "component": self.component,
            "actor": self.actor,
            "result": self.result,
        }

        if self.target:
            entry["target"] = self.target

        if self.parameters:
            # Sanitize parameters (remove potential secrets)
            safe_params = {}
            for k, v in self.parameters.items():
                if any(secret in k.lower() for secret in ["password", "secret", "token", "key", "api_key"]):
                    safe_params[k] = "[REDACTED]"
                else:
                    safe_params[k] = v
            entry["parameters"] = safe_params

        if self.approval_status:
            entry["approval_status"] = self.approval_status

        if self.approval_id:
            entry["approval_id"] = self.approval_id

        if self.error:
            entry["error"] = self.error

        if self.duration_ms is not None:
            entry["duration_ms"] = self.duration_ms

        return entry

    def to_json(self) -> str:
        """Convert entry to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class AuditLogger:
    """
    Audit logger with JSONL format, rotation, and retention.

    Writes structured log entries to daily JSONL files
    and manages automatic cleanup of old logs.
    """

    def __init__(
        self,
        vault_path: str,
        retention_days: int = 90,
    ):
        """
        Initialize audit logger.

        Args:
            vault_path: Path to the Obsidian vault
            retention_days: Days to retain logs (default: 90)
        """
        self.vault_path = Path(vault_path)
        self.logs_path = self.vault_path / "Logs"
        self.retention_days = retention_days

        # Ensure logs directory exists
        self.logs_path.mkdir(parents=True, exist_ok=True)

        # Internal logger
        self._logger = logging.getLogger("AuditLogger")

    def _get_log_file(self, log_date: Optional[date] = None) -> Path:
        """Get log file path for a date."""
        if log_date is None:
            log_date = date.today()
        return self.logs_path / f"{log_date.isoformat()}.jsonl"

    def log_action(
        self,
        action_type: str,
        component: str,
        actor: str,
        target: Optional[str] = None,
        parameters: Optional[dict[str, Any]] = None,
        approval_status: Optional[str] = None,
        approval_id: Optional[str] = None,
        result: str = "success",
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> AuditEntry:
        """
        Log an action.

        Args:
            action_type: Type of action
            component: System component
            actor: Who initiated the action
            target: Target of the action
            parameters: Action parameters
            approval_status: HITL approval status
            approval_id: Approval ID
            result: Action result
            error: Error message if failed
            duration_ms: Action duration

        Returns:
            The created AuditEntry
        """
        entry = AuditEntry(
            action_type=action_type,
            component=component,
            actor=actor,
            target=target,
            parameters=parameters,
            approval_status=approval_status,
            approval_id=approval_id,
            result=result,
            error=error,
            duration_ms=duration_ms,
        )

        # Write to log file (append)
        log_file = self._get_log_file()
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(entry.to_json() + "\n")
        except Exception as e:
            self._logger.error(f"Failed to write audit log: {e}")

        return entry

    def log_success(
        self,
        action_type: str,
        component: str,
        actor: str,
        **kwargs,
    ) -> AuditEntry:
        """Convenience method for logging successful actions."""
        return self.log_action(
            action_type=action_type,
            component=component,
            actor=actor,
            result="success",
            **kwargs,
        )

    def log_failure(
        self,
        action_type: str,
        component: str,
        actor: str,
        error: str,
        **kwargs,
    ) -> AuditEntry:
        """Convenience method for logging failed actions."""
        return self.log_action(
            action_type=action_type,
            component=component,
            actor=actor,
            result="failure",
            error=error,
            **kwargs,
        )

    def query_logs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        action_type: Optional[str] = None,
        component: Optional[str] = None,
        actor: Optional[str] = None,
        result: Optional[str] = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Query audit logs.

        Args:
            start_date: Start date (ISO format, default: 7 days ago)
            end_date: End date (ISO format, default: today)
            action_type: Filter by action type
            component: Filter by component
            actor: Filter by actor
            result: Filter by result
            limit: Maximum entries to return

        Returns:
            List of matching log entries
        """
        # Parse dates
        if end_date:
            end = date.fromisoformat(end_date)
        else:
            end = date.today()

        if start_date:
            start = date.fromisoformat(start_date)
        else:
            start = end - timedelta(days=7)

        entries = []
        current = start

        while current <= end and len(entries) < limit:
            log_file = self._get_log_file(current)

            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if len(entries) >= limit:
                                break

                            try:
                                entry = json.loads(line.strip())

                                # Apply filters
                                if action_type and entry.get("action_type") != action_type:
                                    continue
                                if component and entry.get("component") != component:
                                    continue
                                if actor and entry.get("actor") != actor:
                                    continue
                                if result and entry.get("result") != result:
                                    continue

                                entries.append(entry)

                            except json.JSONDecodeError:
                                continue

                except Exception as e:
                    self._logger.warning(f"Error reading log file {log_file}: {e}")

            current += timedelta(days=1)

        return entries

    def get_stats(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get aggregate statistics from logs.

        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)

        Returns:
            Dict with aggregate statistics
        """
        entries = self.query_logs(start_date, end_date, limit=10000)

        stats = {
            "total_entries": len(entries),
            "by_result": {},
            "by_component": {},
            "by_action_type": {},
        }

        for entry in entries:
            result = entry.get("result", "unknown")
            stats["by_result"][result] = stats["by_result"].get(result, 0) + 1

            component = entry.get("component", "unknown")
            stats["by_component"][component] = stats["by_component"].get(component, 0) + 1

            action = entry.get("action_type", "unknown")
            stats["by_action_type"][action] = stats["by_action_type"].get(action, 0) + 1

        return stats

    def cleanup_old_logs(self) -> int:
        """
        Remove logs older than retention period.

        Returns:
            Number of files deleted
        """
        cutoff = date.today() - timedelta(days=self.retention_days)
        deleted = 0

        for log_file in self.logs_path.glob("*.jsonl"):
            try:
                # Parse date from filename
                file_date_str = log_file.stem  # e.g., "2026-01-25"
                file_date = date.fromisoformat(file_date_str)

                if file_date < cutoff:
                    log_file.unlink()
                    deleted += 1
                    self._logger.info(f"Deleted old log file: {log_file}")

            except (ValueError, OSError) as e:
                self._logger.warning(f"Error processing log file {log_file}: {e}")

        return deleted

    def get_recent_errors(self, hours: int = 24, limit: int = 50) -> list[dict[str, Any]]:
        """
        Get recent error entries.

        Args:
            hours: Look back this many hours
            limit: Maximum entries

        Returns:
            List of error entries
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        errors = []
        current = date.today()
        lookback = (hours // 24) + 1

        for _ in range(lookback + 1):
            log_file = self._get_log_file(current)

            if log_file.exists():
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if len(errors) >= limit:
                                break

                            try:
                                entry = json.loads(line.strip())

                                if entry.get("result") != "failure":
                                    continue

                                timestamp = datetime.fromisoformat(
                                    entry.get("timestamp", "").rstrip("Z")
                                )
                                if timestamp >= cutoff:
                                    errors.append(entry)

                            except (json.JSONDecodeError, ValueError):
                                continue

                except Exception as e:
                    self._logger.warning(f"Error reading log file {log_file}: {e}")

            current -= timedelta(days=1)

        return errors

    def get_status(self) -> dict[str, Any]:
        """Get logger status."""
        log_files = list(self.logs_path.glob("*.jsonl"))
        total_size = sum(f.stat().st_size for f in log_files)

        oldest = None
        newest = None
        if log_files:
            dates = [date.fromisoformat(f.stem) for f in log_files if f.stem.count("-") == 2]
            if dates:
                oldest = min(dates).isoformat()
                newest = max(dates).isoformat()

        return {
            "logs_path": str(self.logs_path),
            "retention_days": self.retention_days,
            "log_file_count": len(log_files),
            "total_size_bytes": total_size,
            "oldest_log": oldest,
            "newest_log": newest,
        }
