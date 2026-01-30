"""
Base Watcher Class - Template for all watchers.

All watchers inherit from this class and implement the abstract methods.
Watchers are the "perception" layer - they monitor inputs and create
action files but NEVER execute actions directly.
"""

import time
import logging
import json
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Any, Optional, Dict


class BaseWatcher(ABC):
    """Abstract base class for all watchers."""

    def __init__(
        self,
        vault_path: str,
        check_interval: int = 60,
        watcher_name: str = "BaseWatcher"
    ):
        """
        Initialize the watcher.

        Args:
            vault_path: Path to the Obsidian vault
            check_interval: Seconds between checks
            watcher_name: Name for logging purposes
        """
        self.vault_path = Path(vault_path)
        self.needs_action = self.vault_path / 'Needs_Action'
        self.logs_path = self.vault_path / 'Logs'
        self.inbox_path = self.vault_path / 'Inbox'
        self.check_interval = check_interval
        self.watcher_name = watcher_name
        self.is_running = False
        self._error_count = 0
        self._max_errors = 5

        # Setup logging
        self.logger = logging.getLogger(watcher_name)
        self.logger.setLevel(logging.INFO)

        # Add console handler if not present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)

        # Ensure directories exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.inbox_path.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def check_for_updates(self) -> List[Any]:
        """
        Check for new items to process.

        Returns:
            List of new items that need action
        """
        pass

    @abstractmethod
    def create_action_file(self, item: Any) -> Path:
        """
        Create a markdown file in Needs_Action folder.

        Args:
            item: The item to create an action file for

        Returns:
            Path to the created file
        """
        pass

    def log_action(self, action_type: str, details: Dict[str, Any]) -> None:
        """Log an action to the daily log file."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'watcher': self.watcher_name,
            'action_type': action_type,
            'details': details
        }

        # Append to log file
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
            except json.JSONDecodeError:
                self.logger.warning(f"Corrupted log file, starting fresh: {log_file}")
                logs = []

        logs.append(log_entry)

        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)

        self.logger.info(f"Logged action: {action_type}")

    def log_heartbeat(self) -> None:
        """Log a heartbeat to indicate watcher is alive."""
        self.log_action('heartbeat', {
            'status': 'alive',
            'error_count': self._error_count
        })

    def run(self) -> None:
        """Main run loop for the watcher."""
        self.logger.info(f'Starting {self.watcher_name}')
        self.log_action('watcher_started', {'interval': self.check_interval})
        self.is_running = True

        while self.is_running:
            try:
                items = self.check_for_updates()

                for item in items:
                    try:
                        filepath = self.create_action_file(item)
                        self.log_action('item_created', {
                            'filepath': str(filepath),
                            'item_summary': str(item)[:100]
                        })
                        self.logger.info(f'Created action file: {filepath}')
                    except Exception as e:
                        self.logger.error(f'Error creating action file: {e}')
                        self.log_action('item_error', {
                            'error': str(e),
                            'item_summary': str(item)[:100]
                        })

                # Reset error count on successful iteration
                self._error_count = 0

            except Exception as e:
                self._error_count += 1
                self.logger.error(f'Error in {self.watcher_name}: {e}')
                self.log_action('error', {
                    'error': str(e),
                    'error_count': self._error_count
                })

                # Graceful degradation: stop after too many consecutive errors
                if self._error_count >= self._max_errors:
                    self.logger.critical(
                        f'{self.watcher_name} exceeded max errors ({self._max_errors}), stopping'
                    )
                    self.log_action('watcher_stopped', {
                        'reason': 'max_errors_exceeded',
                        'error_count': self._error_count
                    })
                    break

            time.sleep(self.check_interval)

    def stop(self) -> None:
        """Stop the watcher gracefully."""
        self.is_running = False
        self.logger.info(f'Stopping {self.watcher_name}')
        self.log_action('watcher_stopped', {'reason': 'manual_stop'})

    def get_status(self) -> Dict[str, Any]:
        """Get current watcher status."""
        return {
            'name': self.watcher_name,
            'is_running': self.is_running,
            'error_count': self._error_count,
            'check_interval': self.check_interval,
            'vault_path': str(self.vault_path)
        }
