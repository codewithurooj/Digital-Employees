"""
Watchers Package - Monitors various inputs and creates action files.

Watchers are the "perception" layer of the AI Employee system.
They monitor inputs (email, files, messages) and create markdown files
in the Needs_Action folder for Claude Code to process.

Available Watchers:
- FileSystemWatcher: Monitors a drop folder for new files
- GmailWatcher: Monitors Gmail for important/unread emails (requires API setup)
- WhatsAppWatcher: Monitors WhatsApp Web for keyword messages (requires Playwright)
- LinkedInWatcher: Monitors LinkedIn for messages, connections, notifications (requires Playwright)
"""

from .base_watcher import BaseWatcher
from .filesystem_watcher import FileSystemWatcher

# Optional imports - graceful fallback if dependencies not installed
try:
    from .gmail_watcher import GmailWatcher
except ImportError:
    GmailWatcher = None

try:
    from .whatsapp_watcher import WhatsAppWatcher
except ImportError:
    WhatsAppWatcher = None

try:
    from .linkedin_watcher import LinkedInWatcher
except ImportError:
    LinkedInWatcher = None

try:
    from .odoo_watcher import OdooWatcher
except ImportError:
    OdooWatcher = None

__all__ = [
    'BaseWatcher',
    'FileSystemWatcher',
    'GmailWatcher',
    'WhatsAppWatcher',
    'LinkedInWatcher',
    'OdooWatcher',
]
