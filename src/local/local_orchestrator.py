"""Local Orchestrator - On-demand local agent entry point.

Pulls updates from Git, processes approvals, merges dashboard updates,
and executes approved actions (send emails, publish posts, post invoices).
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from ..local.sync_puller import SyncPuller
from ..local.dashboard_merger import DashboardMerger

logger = logging.getLogger(__name__)


class LocalOrchestrator:
    """Local agent orchestrator - full execution access.

    Has full permissions to send emails, publish posts, and
    execute payments. Processes approved actions from the vault.
    """

    def __init__(
        self,
        vault_path: str,
        agent_id: str = "local",
        sync_interval: int = 60,
        dry_run: bool = True,
    ):
        self.vault_path = Path(vault_path)
        self.agent_id = agent_id
        self.sync_interval = sync_interval
        self.dry_run = dry_run
        self.logs_path = self.vault_path / "Logs"
        self.logs_path.mkdir(parents=True, exist_ok=True)

        # Sync and dashboard
        self.sync_puller = SyncPuller(
            vault_path=self.vault_path,
            pull_interval=sync_interval,
        )
        self.dashboard_merger = DashboardMerger(vault_path=str(self.vault_path))

        # State
        self.is_running = False
        self._shutdown_event = threading.Event()
        self._threads: dict[str, threading.Thread] = {}

        logger.info(
            f"LocalOrchestrator initialized: agent={agent_id}, dry_run={dry_run}"
        )

    def _pull_on_startup(self) -> None:
        """Pull latest changes from Git on startup."""
        try:
            self.sync_puller.pull_once()
            logger.info("Initial Git pull completed")
        except Exception as e:
            logger.error(f"Initial Git pull failed: {e}")

    def _merge_dashboard_loop(self) -> None:
        """Periodically merge /Updates/ into Dashboard.md."""
        logger.info("Dashboard merger loop started")
        while self.is_running and not self._shutdown_event.is_set():
            try:
                merged = self.dashboard_merger.merge_all_pending()
                if merged:
                    logger.info(f"Merged {len(merged)} dashboard updates")
            except Exception as e:
                logger.error(f"Dashboard merge error: {e}")
            self._shutdown_event.wait(timeout=30)
        logger.info("Dashboard merger loop stopped")

    def _process_approved_actions(self) -> None:
        """Process actions that have been approved."""
        approved_dir = self.vault_path / "Approved"
        if not approved_dir.exists():
            return

        for approved_file in approved_dir.glob("*.md"):
            try:
                content = approved_file.read_text(encoding="utf-8")

                if "status: consumed" in content.lower():
                    continue

                action_type = self._extract_frontmatter(content, "action")
                domain = self._extract_frontmatter(content, "domain")

                if self.dry_run:
                    logger.info(
                        f"[DRY RUN] Would execute approved action: "
                        f"{action_type} ({domain}) from {approved_file.name}"
                    )
                    continue

                result = self._execute_action(action_type, domain, content, approved_file)
                if result.get("success"):
                    self._mark_consumed(approved_file)
                    done_path = self.vault_path / "Done" / approved_file.name
                    done_path.parent.mkdir(parents=True, exist_ok=True)
                    approved_file.rename(done_path)
                    logger.info(f"Executed and completed: {approved_file.name}")
                else:
                    logger.warning(
                        f"Action failed: {approved_file.name} - {result.get('error')}"
                    )

            except Exception as e:
                logger.error(f"Error processing {approved_file.name}: {e}")

    def _extract_frontmatter(self, content: str, key: str) -> str:
        """Extract a value from YAML frontmatter."""
        for line in content.split("\n"):
            if line.startswith(f"{key}:"):
                return line.split(":", 1)[1].strip().strip('"')
        return ""

    def _execute_action(
        self,
        action_type: str,
        domain: str,
        content: str,
        filepath: Path,
    ) -> dict[str, Any]:
        """Execute an approved action.

        In production, this would call the actual MCP servers.
        For now, logs the action.
        """
        self._log_event("execute_action", {
            "action_type": action_type,
            "domain": domain,
            "file": str(filepath),
        })

        # Placeholder for actual MCP execution
        logger.info(f"Executing {action_type} for domain {domain}")
        return {"success": True, "action": action_type}

    def _mark_consumed(self, filepath: Path) -> None:
        """Mark an approval file as consumed."""
        content = filepath.read_text(encoding="utf-8")
        content += f"\n\n---\n*Consumed at: {datetime.now().isoformat()} by {self.agent_id}*\n"
        filepath.write_text(content, encoding="utf-8")

    def _log_event(self, event: str, details: dict) -> None:
        """Log an event."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_path / f"{today}.jsonl"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "component": "local_orchestrator",
            "event": event,
            "details": details,
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def start(self) -> None:
        """Start the local orchestrator."""
        logger.info("=" * 50)
        logger.info("Starting Local Orchestrator")
        logger.info("=" * 50)

        self.is_running = True

        # Pull on startup
        self._pull_on_startup()

        # Start sync puller
        self.sync_puller.start()
        logger.info(f"Sync puller started (interval={self.sync_interval}s)")

        # Start dashboard merger
        merger_thread = threading.Thread(
            target=self._merge_dashboard_loop, name="dashboard-merger", daemon=True
        )
        merger_thread.start()
        self._threads["merger"] = merger_thread

        self._log_event("local_orchestrator_started", {
            "agent_id": self.agent_id,
            "dry_run": self.dry_run,
        })

        logger.info(f"Local orchestrator started: dry_run={self.dry_run}")

    def run(self) -> None:
        """Run the main local orchestrator loop."""
        self.start()
        try:
            while self.is_running and not self._shutdown_event.is_set():
                self._process_approved_actions()
                self.dashboard_merger.merge_all_pending()
                self._shutdown_event.wait(timeout=15)
        except KeyboardInterrupt:
            logger.info("Received interrupt")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the local orchestrator."""
        logger.info("Stopping local orchestrator...")
        self.is_running = False
        self._shutdown_event.set()

        self.sync_puller.stop()

        for name, thread in self._threads.items():
            thread.join(timeout=5)

        self._log_event("local_orchestrator_stopped", {
            "agent_id": self.agent_id,
        })
        logger.info("Local orchestrator stopped")
