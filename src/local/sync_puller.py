"""
Local Sync Puller - Pulls changes from remote vault on startup and periodically.

The local agent uses this to stay in sync with the cloud agent's changes.
"""

import logging
import time
import threading
from pathlib import Path
from typing import Optional

from src.cloud.sync_manager import SyncManager

logger = logging.getLogger(__name__)


class SyncPuller:
    """Periodically pulls vault changes from remote for the local agent."""

    def __init__(
        self,
        vault_path: Path,
        pull_interval: int = 60,
        remote: str = "origin",
        branch: str = "main",
    ):
        self.vault_path = Path(vault_path)
        self.pull_interval = pull_interval
        self.sync_manager = SyncManager(
            vault_path=self.vault_path,
            agent_id="local",
            remote=remote,
            branch=branch,
        )
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_pull_result: Optional[dict] = None

    def pull_once(self) -> dict:
        """Perform a single pull operation."""
        result = self.sync_manager.pull_changes()
        self.last_pull_result = result
        return result

    def start(self) -> None:
        """Start periodic pulling in a background thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("SyncPuller is already running")
            return

        self._stop_event.clear()

        # Pull immediately on startup
        logger.info("SyncPuller: Initial pull on startup")
        self.pull_once()

        # Start periodic pull thread
        self._thread = threading.Thread(
            target=self._pull_loop,
            daemon=True,
            name="sync-puller",
        )
        self._thread.start()
        logger.info(f"SyncPuller started (interval: {self.pull_interval}s)")

    def stop(self) -> None:
        """Stop the periodic pull loop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("SyncPuller stopped")

    def _pull_loop(self) -> None:
        """Background loop that pulls periodically."""
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self.pull_interval)
            if self._stop_event.is_set():
                break
            try:
                result = self.pull_once()
                if result.get("conflicts"):
                    logger.warning(
                        f"Conflicts detected during pull: {result['conflicts']}"
                    )
            except Exception as e:
                logger.error(f"Error during periodic pull: {e}")

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
