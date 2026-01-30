"""Cloud Orchestrator - 24/7 cloud agent entry point.

Runs watchers, processes inbox in draft-only mode, syncs via Git,
and enforces work-zone boundaries (cloud = perception + drafting only).
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..cloud.work_zone import WorkZone, get_zone_from_env
from ..cloud.sync_manager import SyncManager
from ..cloud.health_monitor import HealthMonitor
from ..cloud.cloud_odoo_mcp import CloudOdooMCP
from ..skills.email_triage import EmailTriageSkill
from ..skills.social_draft import SocialDraftSkill

logger = logging.getLogger(__name__)


class CloudOrchestrator:
    """Cloud agent orchestrator - perception and drafting only.

    Enforces WorkZone.CLOUD: can read, triage, draft, and sync,
    but NEVER send, publish, or execute payments.
    """

    def __init__(
        self,
        vault_path: str,
        agent_id: str = "cloud",
        sync_interval: int = 60,
        health_interval: int = 60,
        dry_run: bool = True,
    ):
        self.vault_path = Path(vault_path)
        self.agent_id = agent_id
        self.agent_zone = WorkZone.CLOUD
        self.sync_interval = sync_interval
        self.health_interval = health_interval
        self.dry_run = dry_run
        self.logs_path = self.vault_path / "Logs"
        self.logs_path.mkdir(parents=True, exist_ok=True)

        # Skills (draft-only, cloud-safe)
        self.email_triage = EmailTriageSkill(vault_path=str(self.vault_path))
        self.social_draft = SocialDraftSkill(vault_path=str(self.vault_path))
        self.cloud_odoo = CloudOdooMCP(vault_path=str(self.vault_path))

        # Sync and health
        self.sync_manager = SyncManager(vault_path=str(self.vault_path))
        self.health_monitor = HealthMonitor(
            vault_path=str(self.vault_path),
            agent_id=agent_id,
        )

        # State
        self.is_running = False
        self._shutdown_event = threading.Event()
        self._threads: dict[str, threading.Thread] = {}

        logger.info(
            f"CloudOrchestrator initialized: agent={agent_id}, "
            f"zone={self.agent_zone}, dry_run={dry_run}"
        )

    def _load_watchers(self) -> list[str]:
        """Load cloud-compatible watchers.

        Returns list of loaded watcher names. Actual watcher instantiation
        depends on available credentials and libraries.
        """
        loaded = []

        # Filesystem watcher for Drop folder
        drop_path = self.vault_path / "Drop"
        if drop_path.exists():
            loaded.append("filesystem")
            logger.info(f"Filesystem watcher ready: {drop_path}")

        # Gmail watcher (read-only in cloud)
        try:
            from ..watchers import GmailWatcher
            if GmailWatcher is not None:
                loaded.append("gmail")
                logger.info("Gmail watcher available")
        except (ImportError, Exception):
            logger.info("Gmail watcher not available")

        # Odoo monitor (read-only in cloud)
        try:
            from ..watchers import OdooWatcher
            loaded.append("odoo_monitor")
            logger.info("Odoo monitor available")
        except (ImportError, Exception):
            logger.info("Odoo monitor not available")

        return loaded

    def _sync_loop(self) -> None:
        """Periodic Git sync loop."""
        logger.info(f"Sync loop started (interval={self.sync_interval}s)")
        while self.is_running and not self._shutdown_event.is_set():
            try:
                if not self.dry_run:
                    self.sync_manager.sync()
                else:
                    logger.debug("[DRY RUN] Would sync vault via Git")
            except Exception as e:
                logger.error(f"Sync error: {e}")
                self.health_monitor.log_incident(
                    "sync", str(e), severity="warning"
                )
            self._shutdown_event.wait(timeout=self.sync_interval)
        logger.info("Sync loop stopped")

    def _health_loop(self) -> None:
        """Periodic health check loop."""
        logger.info(f"Health loop started (interval={self.health_interval}s)")
        while self.is_running and not self._shutdown_event.is_set():
            try:
                self.health_monitor.write_status()
            except Exception as e:
                logger.error(f"Health check error: {e}")
            self._shutdown_event.wait(timeout=self.health_interval)
        logger.info("Health loop stopped")

    def _process_needs_action(self) -> None:
        """Process items in Needs_Action subfolders (cloud-safe only)."""
        email_dir = self.vault_path / "Needs_Action" / "email"
        if email_dir.exists():
            for task_file in email_dir.glob("*.md"):
                try:
                    content = task_file.read_text(encoding="utf-8")
                    # Extract email data from the action file
                    email_data = self._parse_action_file(content, task_file)
                    if email_data:
                        self.email_triage.triage_email(email_data)
                        # Move processed file
                        done_path = self.vault_path / "Done" / task_file.name
                        done_path.parent.mkdir(parents=True, exist_ok=True)
                        task_file.rename(done_path)
                        logger.info(f"Triaged email: {task_file.name}")
                except Exception as e:
                    logger.error(f"Error triaging {task_file.name}: {e}")

    def _parse_action_file(self, content: str, filepath: Path) -> Optional[dict]:
        """Parse an action file into email data dict."""
        data: dict[str, Any] = {
            "message_id": filepath.stem,
            "date": datetime.now().isoformat(),
        }
        in_body = False
        body_lines = []

        for line in content.split("\n"):
            if line.startswith("from:"):
                data["from"] = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("subject:"):
                data["subject"] = line.split(":", 1)[1].strip().strip('"')
            elif line.startswith("## Body") or line.startswith("## Message"):
                in_body = True
            elif in_body and line.startswith("##"):
                in_body = False
            elif in_body:
                body_lines.append(line)

        if body_lines:
            data["body"] = "\n".join(body_lines).strip()

        if "from" not in data and "subject" not in data:
            return None

        return data

    def sync_after_task(self) -> None:
        """Sync vault via Git after completing a task."""
        if self.dry_run:
            logger.debug("[DRY RUN] Would sync after task")
            return
        try:
            self.sync_manager.push_changes(commit_message="cloud: task completed")
        except Exception as e:
            logger.error(f"Post-task sync failed: {e}")

    def _log_event(self, event: str, details: dict) -> None:
        """Log an event."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_path / f"{today}.jsonl"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "component": "cloud_orchestrator",
            "event": event,
            "details": details,
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def start(self) -> None:
        """Start the cloud orchestrator."""
        logger.info("=" * 50)
        logger.info("Starting Cloud Orchestrator")
        logger.info("=" * 50)

        self.is_running = True
        watchers = self._load_watchers()

        # Start sync loop
        sync_thread = threading.Thread(
            target=self._sync_loop, name="cloud-sync", daemon=True
        )
        sync_thread.start()
        self._threads["sync"] = sync_thread

        # Start health loop
        health_thread = threading.Thread(
            target=self._health_loop, name="cloud-health", daemon=True
        )
        health_thread.start()
        self._threads["health"] = health_thread

        self._log_event("cloud_orchestrator_started", {
            "agent_id": self.agent_id,
            "zone": str(self.agent_zone),
            "watchers": watchers,
            "dry_run": self.dry_run,
        })

        logger.info(
            f"Cloud orchestrator started: watchers={watchers}, dry_run={self.dry_run}"
        )

    def run(self) -> None:
        """Run the main cloud orchestrator loop."""
        self.start()
        try:
            while self.is_running and not self._shutdown_event.is_set():
                self._process_needs_action()
                self._shutdown_event.wait(timeout=30)
        except KeyboardInterrupt:
            logger.info("Received interrupt")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the cloud orchestrator."""
        logger.info("Stopping cloud orchestrator...")
        self.is_running = False
        self._shutdown_event.set()

        for name, thread in self._threads.items():
            thread.join(timeout=5)

        self._log_event("cloud_orchestrator_stopped", {
            "agent_id": self.agent_id,
        })
        logger.info("Cloud orchestrator stopped")
