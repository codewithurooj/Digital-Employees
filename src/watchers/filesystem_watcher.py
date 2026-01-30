"""
File System Watcher - Monitors a drop folder for new files.

This is the simplest watcher to implement and test. It watches a designated
"Drop" folder and creates action files when new files are added.

Usage:
    python -m src.watchers.filesystem_watcher

Or programmatically:
    from src.watchers import FileSystemWatcher
    watcher = FileSystemWatcher('./AI_Employee_Vault', './AI_Employee_Vault/Drop')
    watcher.run()
"""

import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from .base_watcher import BaseWatcher


class DropFolderHandler(FileSystemEventHandler):
    """Handler for file system events in the drop folder."""

    def __init__(self, watcher: 'FileSystemWatcher'):
        self.watcher = watcher

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle new file creation."""
        if event.is_directory:
            return

        source = Path(event.src_path)
        # Small delay to ensure file is fully written
        time.sleep(0.5)
        self.watcher.process_new_file(source)


class FileSystemWatcher(BaseWatcher):
    """Watch a folder for new files and create action items."""

    def __init__(
        self,
        vault_path: str,
        watch_folder: Optional[str] = None,
        check_interval: int = 5
    ):
        """
        Initialize the file system watcher.

        Args:
            vault_path: Path to the Obsidian vault
            watch_folder: Folder to watch for new files (defaults to vault/Drop)
            check_interval: Seconds between manual checks
        """
        super().__init__(vault_path, check_interval, "FileSystemWatcher")

        # Default watch folder is Drop inside vault
        if watch_folder is None:
            self.watch_folder = self.vault_path / 'Drop'
        else:
            self.watch_folder = Path(watch_folder)

        self.watch_folder.mkdir(parents=True, exist_ok=True)
        self.processed_files: set = set()
        self.observer: Optional[Observer] = None

        # File type classifications
        self.high_priority_ext = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'}
        self.medium_priority_ext = {'.txt', '.csv', '.json', '.xml', '.md'}
        self.image_ext = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}

    def check_for_updates(self) -> List[Path]:
        """Check for new files in watch folder (polling mode)."""
        new_files = []

        for file_path in self.watch_folder.iterdir():
            if file_path.is_file() and file_path.name not in self.processed_files:
                # Skip hidden files and temp files
                if file_path.name.startswith('.') or file_path.name.startswith('~'):
                    continue
                new_files.append(file_path)

        return new_files

    def create_action_file(self, item: Path) -> Path:
        """Create action file for a new file drop."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Get file info
        file_ext = item.suffix.lower()
        file_size = item.stat().st_size
        priority = self._determine_priority(item)
        file_type = self._determine_type(item)

        content = f'''---
type: file_drop
original_name: "{item.name}"
original_path: "{item}"
size_bytes: {file_size}
size_human: "{self._format_size(file_size)}"
extension: "{file_ext}"
file_type: "{file_type}"
received: "{datetime.now().isoformat()}"
priority: "{priority}"
status: pending
requires_approval: false
---

# New File Dropped: {item.name}

## File Details

| Property | Value |
|----------|-------|
| **Name** | {item.name} |
| **Size** | {self._format_size(file_size)} |
| **Type** | {file_type} ({file_ext}) |
| **Priority** | {priority} |
| **Received** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |

## Location

- **Original**: `{item}`
- **Copied to**: `Inbox/{item.name}`

## Suggested Actions

Based on file type "{file_type}":

{self._get_suggested_actions(file_type, file_ext)}

## Processing Notes

<!-- Claude Code will add analysis here -->

## Human Notes

<!-- Add any manual notes here -->

'''
        # Create action file
        safe_name = "".join(c for c in item.stem[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
        action_filename = f'FILE_{timestamp}_{safe_name}.md'
        action_path = self.needs_action / action_filename
        action_path.write_text(content, encoding='utf-8')

        # Copy file to Inbox for processing
        dest_path = self.inbox_path / item.name
        if not dest_path.exists():
            shutil.copy2(item, dest_path)
            self.logger.info(f'Copied file to Inbox: {dest_path}')

        # Mark as processed
        self.processed_files.add(item.name)

        return action_path

    def process_new_file(self, file_path: Path) -> None:
        """Process a newly detected file (used by watchdog observer)."""
        if file_path.name not in self.processed_files:
            if file_path.name.startswith('.') or file_path.name.startswith('~'):
                return

            try:
                action_path = self.create_action_file(file_path)
                self.log_action('file_processed', {
                    'original_file': str(file_path),
                    'action_file': str(action_path),
                    'size': file_path.stat().st_size
                })
            except Exception as e:
                self.logger.error(f'Error processing file {file_path}: {e}')
                self.log_action('file_error', {
                    'file': str(file_path),
                    'error': str(e)
                })

    def _determine_priority(self, file_path: Path) -> str:
        """Determine priority based on file type and name."""
        ext = file_path.suffix.lower()
        name_lower = file_path.name.lower()

        # Check for urgent keywords in filename
        urgent_keywords = ['urgent', 'asap', 'important', 'invoice', 'payment', 'contract']
        if any(kw in name_lower for kw in urgent_keywords):
            return 'high'

        if ext in self.high_priority_ext:
            return 'high'
        elif ext in self.medium_priority_ext:
            return 'medium'
        return 'low'

    def _determine_type(self, file_path: Path) -> str:
        """Categorize file by type."""
        ext = file_path.suffix.lower()

        if ext in self.high_priority_ext:
            return 'document'
        elif ext in self.medium_priority_ext:
            return 'data'
        elif ext in self.image_ext:
            return 'image'
        elif ext in {'.zip', '.rar', '.7z', '.tar', '.gz'}:
            return 'archive'
        elif ext in {'.mp3', '.wav', '.flac', '.m4a'}:
            return 'audio'
        elif ext in {'.mp4', '.avi', '.mkv', '.mov'}:
            return 'video'
        elif ext in {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs'}:
            return 'code'
        return 'other'

    def _format_size(self, size: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'

    def _get_suggested_actions(self, file_type: str, ext: str) -> str:
        """Get suggested actions based on file type."""
        actions = {
            'document': '''- [ ] Review document contents
- [ ] Extract key information
- [ ] File in appropriate category
- [ ] Check if response/action needed''',
            'data': '''- [ ] Validate data format
- [ ] Import to relevant system
- [ ] Archive original file''',
            'image': '''- [ ] Review image
- [ ] Add to media library if needed
- [ ] Check for sensitive content''',
            'archive': '''- [ ] Extract contents
- [ ] Review extracted files
- [ ] Process individual items''',
            'code': '''- [ ] Review code purpose
- [ ] Check for security concerns
- [ ] File appropriately''',
        }
        return actions.get(file_type, '''- [ ] Review file contents
- [ ] Determine appropriate action
- [ ] File or archive as needed''')

    def run_with_observer(self) -> None:
        """Run using watchdog observer for real-time monitoring."""
        self.logger.info(f'Starting FileSystemWatcher (observer mode) on {self.watch_folder}')
        self.log_action('watcher_started', {
            'mode': 'observer',
            'watch_folder': str(self.watch_folder)
        })

        event_handler = DropFolderHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.watch_folder), recursive=False)
        self.observer.start()
        self.is_running = True

        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info('Received interrupt, stopping...')
        finally:
            self.observer.stop()
            self.observer.join()
            self.log_action('watcher_stopped', {'mode': 'observer'})


# Standalone runner
if __name__ == '__main__':
    import argparse
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description='File System Watcher for AI Employee')
    parser.add_argument(
        '--vault',
        default='./AI_Employee_Vault',
        help='Path to Obsidian vault'
    )
    parser.add_argument(
        '--watch',
        default=None,
        help='Folder to watch (defaults to vault/Drop)'
    )
    parser.add_argument(
        '--mode',
        choices=['poll', 'observer'],
        default='observer',
        help='Watch mode: poll (interval check) or observer (real-time)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Check interval in seconds (for poll mode)'
    )

    args = parser.parse_args()

    watcher = FileSystemWatcher(
        vault_path=args.vault,
        watch_folder=args.watch,
        check_interval=args.interval
    )

    print(f"Watching folder: {watcher.watch_folder}")
    print(f"Action files will be created in: {watcher.needs_action}")
    print("Press Ctrl+C to stop...")

    if args.mode == 'observer':
        watcher.run_with_observer()
    else:
        watcher.run()
