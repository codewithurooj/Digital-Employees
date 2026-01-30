# Personal AI Employee - Complete Build Roadmap

> **Goal**: Build an autonomous Digital FTE (Full-Time Equivalent) that manages personal and business affairs 24/7 using Claude Code + Obsidian.

---

## Table of Contents

1. [Overview & Architecture](#overview--architecture)
2. [Phase 0: Prerequisites & Setup](#phase-0-prerequisites--setup)
3. [Phase 1: Bronze Tier - Foundation](#phase-1-bronze-tier---foundation)
4. [Phase 2: Silver Tier - Functional Assistant](#phase-2-silver-tier---functional-assistant)
5. [Phase 3: Gold Tier - Autonomous Employee](#phase-3-gold-tier---autonomous-employee)
6. [Phase 4: Platinum Tier - Cloud Deployment](#phase-4-platinum-tier---cloud-deployment)
7. [Security Implementation](#security-implementation)
8. [Testing & Validation](#testing--validation)
9. [Resources & References](#resources--references)

---

## Overview & Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    PERSONAL AI EMPLOYEE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   WATCHERS  │───>│   OBSIDIAN  │<───│ CLAUDE CODE │         │
│  │  (Sensors)  │    │   (Memory)  │    │   (Brain)   │         │
│  └─────────────┘    └─────────────┘    └──────┬──────┘         │
│         │                                      │                │
│         │           ┌─────────────┐           │                │
│         └──────────>│     MCP     │<──────────┘                │
│                     │   (Hands)   │                            │
│                     └──────┬──────┘                            │
│                            │                                   │
│                     ┌──────▼──────┐                            │
│                     │  EXTERNAL   │                            │
│                     │   ACTIONS   │                            │
│                     └─────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### Core Flow

```
Perception (Watchers) → Reasoning (Claude Code) → Action (MCP Servers)
         ↓                      ↓                        ↓
   Monitor inputs      Read → Think → Plan        Execute actions
   Create .md files    Write to Obsidian          With HITL approval
```

### Tier Summary

| Tier | Scope | Effort | Key Deliverables |
|------|-------|--------|------------------|
| Bronze | Foundation | 8-12 hrs | Vault + 1 Watcher + Claude integration |
| Silver | Functional | 20-30 hrs | Multiple Watchers + MCP + HITL + Scheduling |
| Gold | Autonomous | 40+ hrs | Full integration + Odoo + CEO Briefing |
| Platinum | Production | 60+ hrs | Cloud 24/7 + Multi-agent + Sync |

---

## Phase 0: Prerequisites & Setup

### Checklist

- [ ] **0.1** Install Claude Code
- [ ] **0.2** Install Obsidian v1.10.6+
- [ ] **0.3** Install Python 3.13+
- [ ] **0.4** Install Node.js v24+ LTS
- [ ] **0.5** Install GitHub Desktop
- [ ] **0.6** Set up UV Python project
- [ ] **0.7** Verify all installations

### 0.1 Install Claude Code

```bash
# Option 1: With Anthropic subscription
npm install -g @anthropic/claude-code

# Option 2: Using Claude Code Router (free Gemini API)
# See: https://github.com/anthropics/claude-code-router
```

### 0.2 Install Obsidian

Download from: https://obsidian.md/download

- Version required: v1.10.6 or higher
- Create new vault named: `AI_Employee_Vault`

### 0.3 Install Python 3.13+

```bash
# Using UV (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create project
uv init ai-employee
cd ai-employee
uv venv
uv pip install watchdog playwright google-api-python-client python-dotenv
```

### 0.4 Install Node.js v24+ LTS

Download from: https://nodejs.org/

```bash
# Verify installation
node --version  # Should be v24+
npm --version
```

### 0.5 Verify All Installations

```bash
claude --version
python --version
node --version
obsidian --version  # Or check in Obsidian > About
```

### 0.6 Project Structure Setup

```bash
# Create project structure
mkdir -p AI_Employee_Vault/{Inbox,Needs_Action,Plans,Pending_Approval,Approved,Rejected,Done,Logs,Accounting,Briefings,Invoices}
mkdir -p src/{watchers,mcp_servers,skills,utils}
mkdir -p config
mkdir -p tests
```

**Expected Structure:**
```
Digital-Employees/
├── AI_Employee_Vault/           # Obsidian Vault
│   ├── Inbox/
│   ├── Needs_Action/
│   ├── Plans/
│   ├── Pending_Approval/
│   ├── Approved/
│   ├── Rejected/
│   ├── Done/
│   ├── Logs/
│   ├── Accounting/
│   ├── Briefings/
│   ├── Invoices/
│   ├── Dashboard.md
│   ├── Company_Handbook.md
│   └── Business_Goals.md
├── src/
│   ├── watchers/
│   │   ├── __init__.py
│   │   ├── base_watcher.py
│   │   ├── gmail_watcher.py
│   │   ├── whatsapp_watcher.py
│   │   └── filesystem_watcher.py
│   ├── mcp_servers/
│   │   ├── email-mcp/
│   │   ├── browser-mcp/
│   │   └── odoo-mcp/
│   ├── skills/
│   │   └── (Claude Agent Skills)
│   └── utils/
│       ├── retry_handler.py
│       └── audit_logger.py
├── config/
│   ├── mcp.json
│   └── watchers.json
├── orchestrator.py
├── watchdog.py
├── .env                         # NEVER commit this
├── .env.example
├── .gitignore
├── requirements.txt
├── package.json
└── README.md
```

---

## Phase 1: Bronze Tier - Foundation

**Goal**: Obsidian vault + One working Watcher + Claude Code integration

### Checklist

- [ ] **1.1** Create Obsidian Vault with folder structure
- [ ] **1.2** Create Dashboard.md
- [ ] **1.3** Create Company_Handbook.md
- [ ] **1.4** Create base watcher class
- [ ] **1.5** Implement File System Watcher (easiest to start)
- [ ] **1.6** Connect Claude Code to vault
- [ ] **1.7** Test end-to-end flow
- [ ] **1.8** Create first Agent Skill

### 1.1 Create Obsidian Vault

Open Obsidian → Create new vault → Name it `AI_Employee_Vault`

Create the folder structure as shown above.

### 1.2 Create Dashboard.md

```markdown
# AI Employee Dashboard

> Last Updated: {{date}}

## System Status
- **Status**: 🟢 Online
- **Active Watchers**: 0
- **Pending Actions**: 0
- **Awaiting Approval**: 0

## Quick Stats

### Today
| Metric | Value |
|--------|-------|
| Emails Processed | 0 |
| Tasks Completed | 0 |
| Approvals Pending | 0 |

### This Week
| Metric | Value |
|--------|-------|
| Revenue | $0 |
| Expenses | $0 |
| Tasks Completed | 0 |

## Recent Activity

<!-- Auto-updated by AI Employee -->

## Pending Actions

<!-- Items requiring attention -->

## Upcoming Deadlines

<!-- Auto-populated from tasks -->

---
*Dashboard auto-updated by AI Employee*
```

### 1.3 Create Company_Handbook.md

```markdown
# Company Handbook - Rules of Engagement

> These rules govern how the AI Employee operates.

## Communication Rules

### Email
- Always be professional and polite
- Response time target: < 24 hours for important emails
- Flag emails from unknown senders for review
- Never send emails with attachments > 10MB without approval

### WhatsApp
- Use friendly but professional tone
- Respond to urgent keywords immediately: "urgent", "asap", "help"
- Never share sensitive information via WhatsApp

### Social Media
- All posts require human approval before publishing
- Maintain brand voice consistency
- No political or controversial content

## Financial Rules

### Payments
- **Auto-approve threshold**: $50 for recurring payments to known vendors
- **Always require approval**:
  - Any payment > $100
  - Payments to new recipients
  - International transfers
- **Never auto-approve**:
  - Cryptocurrency transactions
  - Wire transfers
  - Payments to personal accounts

### Invoicing
- Standard payment terms: Net 30
- Send payment reminders at: 7 days, 3 days, 1 day before due
- Flag overdue invoices > 30 days

## Security Rules

- Never share credentials or API keys
- Never bypass approval workflows
- Log all actions for audit trail
- Immediately flag suspicious activity

## Escalation Triggers

Escalate to human immediately if:
1. Payment amount > $500
2. Legal documents or contracts
3. Customer complaints
4. Security concerns
5. Uncertain about correct action

## Working Hours

- **Active monitoring**: 24/7
- **Human escalation**: 9 AM - 6 PM local time
- **Urgent after-hours**: Email + SMS notification
```

### 1.4 Create Base Watcher Class

**File: `src/watchers/base_watcher.py`**

```python
"""
Base Watcher Class - Template for all watchers
All watchers inherit from this class and implement the abstract methods.
"""

import time
import logging
import json
from pathlib import Path
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Any, Optional

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
        self.check_interval = check_interval
        self.watcher_name = watcher_name
        self.is_running = False

        # Setup logging
        self.logger = logging.getLogger(watcher_name)
        self.logger.setLevel(logging.INFO)

        # Ensure directories exist
        self.needs_action.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)

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

    def log_action(self, action_type: str, details: dict) -> None:
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
            with open(log_file, 'r') as f:
                logs = json.load(f)

        logs.append(log_entry)

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

        self.logger.info(f"Logged action: {action_type}")

    def run(self) -> None:
        """Main run loop for the watcher."""
        self.logger.info(f'Starting {self.watcher_name}')
        self.is_running = True

        while self.is_running:
            try:
                items = self.check_for_updates()

                for item in items:
                    filepath = self.create_action_file(item)
                    self.log_action('item_created', {
                        'filepath': str(filepath),
                        'item_summary': str(item)[:100]
                    })
                    self.logger.info(f'Created action file: {filepath}')

            except Exception as e:
                self.logger.error(f'Error in {self.watcher_name}: {e}')
                self.log_action('error', {'error': str(e)})

            time.sleep(self.check_interval)

    def stop(self) -> None:
        """Stop the watcher."""
        self.is_running = False
        self.logger.info(f'Stopping {self.watcher_name}')
```

### 1.5 Implement File System Watcher

**File: `src/watchers/filesystem_watcher.py`**

```python
"""
File System Watcher - Monitors a drop folder for new files
This is the simplest watcher to implement and test.
"""

import shutil
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from .base_watcher import BaseWatcher

class DropFolderHandler(FileSystemEventHandler):
    """Handler for file system events."""

    def __init__(self, watcher: 'FileSystemWatcher'):
        self.watcher = watcher

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle new file creation."""
        if event.is_directory:
            return

        source = Path(event.src_path)
        self.watcher.process_new_file(source)


class FileSystemWatcher(BaseWatcher):
    """Watch a folder for new files and create action items."""

    def __init__(
        self,
        vault_path: str,
        watch_folder: str,
        check_interval: int = 5
    ):
        super().__init__(vault_path, check_interval, "FileSystemWatcher")
        self.watch_folder = Path(watch_folder)
        self.watch_folder.mkdir(parents=True, exist_ok=True)
        self.processed_files = set()
        self.observer = None

    def check_for_updates(self) -> list:
        """Check for new files in watch folder."""
        new_files = []

        for file_path in self.watch_folder.iterdir():
            if file_path.is_file() and file_path.name not in self.processed_files:
                new_files.append(file_path)

        return new_files

    def create_action_file(self, item: Path) -> Path:
        """Create action file for a new file drop."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Determine file type and priority
        file_ext = item.suffix.lower()
        priority = self._determine_priority(item)

        content = f'''---
type: file_drop
original_name: {item.name}
original_path: {item}
size: {item.stat().st_size}
extension: {file_ext}
received: {datetime.now().isoformat()}
priority: {priority}
status: pending
---

# New File Dropped: {item.name}

## File Details
- **Name**: {item.name}
- **Size**: {self._format_size(item.stat().st_size)}
- **Type**: {file_ext}
- **Received**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Suggested Actions
- [ ] Review file contents
- [ ] Categorize appropriately
- [ ] Process or archive

## Notes
<!-- Add any notes here -->

'''
        # Create action file
        action_filename = f'FILE_{timestamp}_{item.stem}.md'
        action_path = self.needs_action / action_filename
        action_path.write_text(content, encoding='utf-8')

        # Copy file to vault for processing
        dest_path = self.vault_path / 'Inbox' / item.name
        shutil.copy2(item, dest_path)

        # Mark as processed
        self.processed_files.add(item.name)

        return action_path

    def process_new_file(self, file_path: Path) -> None:
        """Process a newly detected file."""
        if file_path.name not in self.processed_files:
            action_path = self.create_action_file(file_path)
            self.log_action('file_processed', {
                'original_file': str(file_path),
                'action_file': str(action_path)
            })

    def _determine_priority(self, file_path: Path) -> str:
        """Determine priority based on file type."""
        high_priority_ext = ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
        medium_priority_ext = ['.txt', '.csv', '.json']

        ext = file_path.suffix.lower()

        if ext in high_priority_ext:
            return 'high'
        elif ext in medium_priority_ext:
            return 'medium'
        return 'low'

    def _format_size(self, size: int) -> str:
        """Format file size in human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f'{size:.1f} {unit}'
            size /= 1024
        return f'{size:.1f} TB'

    def run_with_observer(self) -> None:
        """Run using watchdog observer for real-time monitoring."""
        self.logger.info(f'Starting FileSystemWatcher on {self.watch_folder}')

        event_handler = DropFolderHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.watch_folder), recursive=False)
        self.observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()

        self.observer.join()


# Standalone runner
if __name__ == '__main__':
    import time
    import logging

    logging.basicConfig(level=logging.INFO)

    # Configure paths
    VAULT_PATH = '../AI_Employee_Vault'
    WATCH_FOLDER = '../AI_Employee_Vault/Drop'

    watcher = FileSystemWatcher(VAULT_PATH, WATCH_FOLDER)
    watcher.run_with_observer()
```

### 1.6 Create Gmail Watcher (Alternative First Watcher)

**File: `src/watchers/gmail_watcher.py`**

```python
"""
Gmail Watcher - Monitors Gmail for important/unread emails
Requires Google API credentials setup.
"""

import os
import base64
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from .base_watcher import BaseWatcher

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailWatcher(BaseWatcher):
    """Watch Gmail for new important/unread emails."""

    def __init__(
        self,
        vault_path: str,
        credentials_path: str,
        token_path: str = 'token.json',
        check_interval: int = 120,
        query: str = 'is:unread is:important'
    ):
        super().__init__(vault_path, check_interval, "GmailWatcher")
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.query = query
        self.processed_ids = set()
        self.service = None

        # Initialize Gmail service
        self._initialize_service()

    def _initialize_service(self) -> None:
        """Initialize Gmail API service."""
        creds = None

        # Load existing token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        self.service = build('gmail', 'v1', credentials=creds)
        self.logger.info("Gmail service initialized")

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """Check for new unread important emails."""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=self.query,
                maxResults=10
            ).execute()

            messages = results.get('messages', [])
            new_messages = []

            for msg in messages:
                if msg['id'] not in self.processed_ids:
                    # Get full message details
                    full_msg = self.service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    new_messages.append(full_msg)

            return new_messages

        except Exception as e:
            self.logger.error(f"Error checking Gmail: {e}")
            return []

    def create_action_file(self, item: Dict[str, Any]) -> Path:
        """Create action file for an email."""
        msg_id = item['id']
        headers = {h['name']: h['value'] for h in item['payload']['headers']}

        # Extract email details
        sender = headers.get('From', 'Unknown')
        subject = headers.get('Subject', 'No Subject')
        date = headers.get('Date', '')

        # Get email snippet/body
        snippet = item.get('snippet', '')

        # Determine priority
        labels = item.get('labelIds', [])
        priority = 'high' if 'IMPORTANT' in labels else 'medium'

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        content = f'''---
type: email
message_id: {msg_id}
from: {sender}
subject: {subject}
date: {date}
received: {datetime.now().isoformat()}
priority: {priority}
status: pending
labels: {', '.join(labels)}
---

# Email: {subject}

## Details
- **From**: {sender}
- **Date**: {date}
- **Priority**: {priority}

## Preview
{snippet}

## Suggested Actions
- [ ] Reply to sender
- [ ] Forward to relevant party
- [ ] Archive after processing
- [ ] Flag for follow-up

## Draft Response
<!-- Write your response here -->

## Notes
<!-- Add any notes here -->

'''
        # Create action file
        safe_subject = "".join(c for c in subject[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
        action_filename = f'EMAIL_{timestamp}_{safe_subject}.md'
        action_path = self.needs_action / action_filename
        action_path.write_text(content, encoding='utf-8')

        # Mark as processed
        self.processed_ids.add(msg_id)

        return action_path


# Standalone runner
if __name__ == '__main__':
    import logging

    logging.basicConfig(level=logging.INFO)

    VAULT_PATH = '../AI_Employee_Vault'
    CREDENTIALS_PATH = '../config/gmail_credentials.json'

    watcher = GmailWatcher(VAULT_PATH, CREDENTIALS_PATH)
    watcher.run()
```

### 1.7 Connect Claude Code to Vault

**Create Claude Code settings:**

**File: `.claude/settings.json`**

```json
{
  "workingDirectory": "./AI_Employee_Vault",
  "defaultModel": "claude-sonnet-4-20250514",
  "permissions": {
    "allowedDirectories": [
      "./AI_Employee_Vault",
      "./src"
    ]
  }
}
```

**Test Claude Code integration:**

```bash
# Navigate to vault directory
cd AI_Employee_Vault

# Start Claude Code
claude

# Test by asking Claude to:
# 1. Read Dashboard.md
# 2. Check Needs_Action folder
# 3. Create a test Plan.md
```

### 1.8 Create First Agent Skill

**File: `.claude/commands/process-inbox.md`**

```markdown
# Process Inbox Skill

Process all items in the Needs_Action folder and create appropriate plans.

## Instructions

1. Read all .md files in /Needs_Action folder
2. For each item:
   - Analyze the content and type
   - Determine required actions based on Company_Handbook.md rules
   - Create a Plan.md file in /Plans folder
   - If action requires approval, create file in /Pending_Approval
3. Update Dashboard.md with current status
4. Move processed items based on status

## Output Format

For each processed item, create a plan file:

```
/Plans/PLAN_{timestamp}_{item_type}.md
```

## Rules to Follow

- Follow all rules in Company_Handbook.md
- Never auto-approve payments > $100
- Always log actions
- Flag uncertain items for human review
```

---

## Phase 2: Silver Tier - Functional Assistant

**Goal**: Multiple Watchers + MCP Server + Human-in-the-Loop + Scheduling

### Checklist

- [ ] **2.1** Implement WhatsApp Watcher
- [ ] **2.2** Implement LinkedIn Watcher
- [ ] **2.3** Build Email MCP Server
- [ ] **2.4** Implement HITL approval workflow
- [ ] **2.5** Create Claude reasoning loop
- [ ] **2.6** Set up scheduling (cron/Task Scheduler)
- [ ] **2.7** Create LinkedIn auto-posting skill
- [ ] **2.8** Build orchestrator

### 2.1 WhatsApp Watcher (Playwright-based)

**File: `src/watchers/whatsapp_watcher.py`**

```python
"""
WhatsApp Watcher - Monitors WhatsApp Web for messages
Uses Playwright for browser automation.

WARNING: Be aware of WhatsApp's terms of service.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright, Browser, Page
from .base_watcher import BaseWatcher


class WhatsAppWatcher(BaseWatcher):
    """Watch WhatsApp Web for important messages."""

    def __init__(
        self,
        vault_path: str,
        session_path: str,
        check_interval: int = 30,
        keywords: List[str] = None
    ):
        super().__init__(vault_path, check_interval, "WhatsAppWatcher")
        self.session_path = Path(session_path)
        self.session_path.mkdir(parents=True, exist_ok=True)

        # Keywords that trigger action creation
        self.keywords = keywords or [
            'urgent', 'asap', 'invoice', 'payment',
            'help', 'important', 'deadline', 'meeting'
        ]

        self.processed_messages = set()

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """Check WhatsApp Web for new messages matching keywords."""
        messages = []

        try:
            with sync_playwright() as p:
                # Use persistent context to maintain login
                browser = p.chromium.launch_persistent_context(
                    str(self.session_path),
                    headless=False,  # Set True after initial login
                    args=['--disable-blink-features=AutomationControlled']
                )

                page = browser.pages[0] if browser.pages else browser.new_page()

                # Navigate to WhatsApp Web
                page.goto('https://web.whatsapp.com')

                # Wait for chat list to load (indicates logged in)
                try:
                    page.wait_for_selector('[data-testid="chat-list"]', timeout=60000)
                except:
                    self.logger.warning("WhatsApp not logged in or timeout")
                    browser.close()
                    return []

                # Find unread chats
                unread_chats = page.query_selector_all('[aria-label*="unread"]')

                for chat in unread_chats:
                    try:
                        # Get chat preview text
                        preview_text = chat.inner_text().lower()

                        # Check if any keyword matches
                        if any(kw in preview_text for kw in self.keywords):
                            # Click chat to get full message
                            chat.click()
                            page.wait_for_timeout(1000)

                            # Get sender and message details
                            contact_name = self._get_contact_name(page)
                            last_message = self._get_last_message(page)

                            msg_id = f"{contact_name}_{hash(last_message)}"

                            if msg_id not in self.processed_messages:
                                messages.append({
                                    'id': msg_id,
                                    'contact': contact_name,
                                    'message': last_message,
                                    'preview': preview_text[:200],
                                    'matched_keywords': [
                                        kw for kw in self.keywords
                                        if kw in preview_text
                                    ]
                                })

                    except Exception as e:
                        self.logger.error(f"Error processing chat: {e}")

                browser.close()

        except Exception as e:
            self.logger.error(f"Error in WhatsApp watcher: {e}")

        return messages

    def _get_contact_name(self, page: Page) -> str:
        """Get the contact name from current chat."""
        try:
            header = page.query_selector('[data-testid="conversation-header"]')
            if header:
                return header.inner_text().split('\n')[0]
        except:
            pass
        return "Unknown"

    def _get_last_message(self, page: Page) -> str:
        """Get the last message from current chat."""
        try:
            messages = page.query_selector_all('[data-testid="msg-container"]')
            if messages:
                return messages[-1].inner_text()
        except:
            pass
        return ""

    def create_action_file(self, item: Dict[str, Any]) -> Path:
        """Create action file for WhatsApp message."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        content = f'''---
type: whatsapp
message_id: {item['id']}
contact: {item['contact']}
received: {datetime.now().isoformat()}
priority: high
status: pending
matched_keywords: {', '.join(item['matched_keywords'])}
---

# WhatsApp Message from {item['contact']}

## Message
{item['message']}

## Matched Keywords
{', '.join(item['matched_keywords'])}

## Suggested Actions
- [ ] Reply to message
- [ ] Create task/reminder
- [ ] Forward to email
- [ ] Archive

## Draft Response
<!-- Write your response here -->

## Notes
<!-- Add any notes here -->

'''
        # Create action file
        safe_contact = "".join(c for c in item['contact'][:20] if c.isalnum() or c in (' ', '-', '_')).strip()
        action_filename = f'WHATSAPP_{timestamp}_{safe_contact}.md'
        action_path = self.needs_action / action_filename
        action_path.write_text(content, encoding='utf-8')

        self.processed_messages.add(item['id'])

        return action_path
```

### 2.2 Build Email MCP Server

**File: `src/mcp_servers/email-mcp/index.js`**

```javascript
/**
 * Email MCP Server
 * Provides email sending capabilities to Claude Code
 */

const { Server } = require('@modelcontextprotocol/sdk/server');
const { StdioServerTransport } = require('@modelcontextprotocol/sdk/server/stdio');
const nodemailer = require('nodemailer');

// Configuration from environment
const EMAIL_USER = process.env.EMAIL_USER;
const EMAIL_PASS = process.env.EMAIL_PASS;
const EMAIL_HOST = process.env.EMAIL_HOST || 'smtp.gmail.com';
const EMAIL_PORT = process.env.EMAIL_PORT || 587;
const DRY_RUN = process.env.DRY_RUN === 'true';

// Create transporter
const transporter = nodemailer.createTransport({
  host: EMAIL_HOST,
  port: EMAIL_PORT,
  secure: false,
  auth: {
    user: EMAIL_USER,
    pass: EMAIL_PASS,
  },
});

// Create MCP Server
const server = new Server({
  name: 'email-mcp',
  version: '1.0.0',
});

// Define tools
server.setRequestHandler('tools/list', async () => ({
  tools: [
    {
      name: 'send_email',
      description: 'Send an email',
      inputSchema: {
        type: 'object',
        properties: {
          to: { type: 'string', description: 'Recipient email address' },
          subject: { type: 'string', description: 'Email subject' },
          body: { type: 'string', description: 'Email body (plain text or HTML)' },
          isHtml: { type: 'boolean', description: 'Whether body is HTML', default: false },
        },
        required: ['to', 'subject', 'body'],
      },
    },
    {
      name: 'draft_email',
      description: 'Create an email draft (does not send)',
      inputSchema: {
        type: 'object',
        properties: {
          to: { type: 'string', description: 'Recipient email address' },
          subject: { type: 'string', description: 'Email subject' },
          body: { type: 'string', description: 'Email body' },
        },
        required: ['to', 'subject', 'body'],
      },
    },
  ],
}));

// Handle tool calls
server.setRequestHandler('tools/call', async (request) => {
  const { name, arguments: args } = request.params;

  if (name === 'send_email') {
    if (DRY_RUN) {
      console.log(`[DRY RUN] Would send email to: ${args.to}`);
      return {
        content: [
          {
            type: 'text',
            text: `[DRY RUN] Email would be sent to ${args.to} with subject: ${args.subject}`,
          },
        ],
      };
    }

    try {
      const info = await transporter.sendMail({
        from: EMAIL_USER,
        to: args.to,
        subject: args.subject,
        [args.isHtml ? 'html' : 'text']: args.body,
      });

      return {
        content: [
          {
            type: 'text',
            text: `Email sent successfully. Message ID: ${info.messageId}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: `Failed to send email: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }

  if (name === 'draft_email') {
    // Save draft to file for review
    const draft = {
      to: args.to,
      subject: args.subject,
      body: args.body,
      created: new Date().toISOString(),
    };

    return {
      content: [
        {
          type: 'text',
          text: `Draft created:\n${JSON.stringify(draft, null, 2)}`,
        },
      ],
    };
  }

  return {
    content: [{ type: 'text', text: `Unknown tool: ${name}` }],
    isError: true,
  };
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Email MCP Server running');
}

main().catch(console.error);
```

**File: `src/mcp_servers/email-mcp/package.json`**

```json
{
  "name": "email-mcp",
  "version": "1.0.0",
  "main": "index.js",
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "nodemailer": "^6.9.0"
  }
}
```

### 2.3 Configure MCP in Claude Code

**File: `config/mcp.json`**

```json
{
  "mcpServers": {
    "email": {
      "command": "node",
      "args": ["./src/mcp_servers/email-mcp/index.js"],
      "env": {
        "EMAIL_USER": "${EMAIL_USER}",
        "EMAIL_PASS": "${EMAIL_PASS}",
        "DRY_RUN": "true"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./AI_Employee_Vault"]
    }
  }
}
```

### 2.4 Implement HITL Approval Workflow

**File: `src/utils/approval_handler.py`**

```python
"""
Human-in-the-Loop Approval Handler
Manages approval requests and monitors approved actions.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileMovedEvent


class ApprovalRequest:
    """Represents an approval request."""

    def __init__(
        self,
        action_type: str,
        details: Dict[str, Any],
        vault_path: str,
        expires_hours: int = 24
    ):
        self.action_type = action_type
        self.details = details
        self.vault_path = Path(vault_path)
        self.created = datetime.now()
        self.expires = self.created + timedelta(hours=expires_hours)
        self.request_id = f"{action_type}_{self.created.strftime('%Y%m%d_%H%M%S')}"

    def create_approval_file(self) -> Path:
        """Create approval request file."""
        pending_dir = self.vault_path / 'Pending_Approval'
        pending_dir.mkdir(parents=True, exist_ok=True)

        content = f'''---
type: approval_request
request_id: {self.request_id}
action_type: {self.action_type}
created: {self.created.isoformat()}
expires: {self.expires.isoformat()}
status: pending
---

# Approval Required: {self.action_type.replace('_', ' ').title()}

## Action Details
```json
{json.dumps(self.details, indent=2)}
```

## Instructions

**To Approve**: Move this file to `/Approved/` folder
**To Reject**: Move this file to `/Rejected/` folder

## Expiration
This request expires at: {self.expires.strftime('%Y-%m-%d %H:%M:%S')}

---
*Automated approval request - Review carefully before approving*
'''

        filepath = pending_dir / f'{self.request_id}.md'
        filepath.write_text(content, encoding='utf-8')

        return filepath


class ApprovalHandler(FileSystemEventHandler):
    """Watches for approved files and triggers actions."""

    def __init__(
        self,
        vault_path: str,
        action_callbacks: Dict[str, Callable]
    ):
        self.vault_path = Path(vault_path)
        self.approved_dir = self.vault_path / 'Approved'
        self.rejected_dir = self.vault_path / 'Rejected'
        self.done_dir = self.vault_path / 'Done'
        self.action_callbacks = action_callbacks

        # Ensure directories exist
        self.approved_dir.mkdir(parents=True, exist_ok=True)
        self.rejected_dir.mkdir(parents=True, exist_ok=True)
        self.done_dir.mkdir(parents=True, exist_ok=True)

    def on_created(self, event):
        """Handle file created in Approved folder."""
        if event.is_directory:
            return

        filepath = Path(event.src_path)

        # Only process files in Approved directory
        if filepath.parent != self.approved_dir:
            return

        self._process_approved_file(filepath)

    def _process_approved_file(self, filepath: Path) -> None:
        """Process an approved request."""
        try:
            content = filepath.read_text(encoding='utf-8')

            # Parse action type from filename or content
            action_type = self._extract_action_type(filepath.stem, content)

            if action_type in self.action_callbacks:
                # Execute the callback
                callback = self.action_callbacks[action_type]
                details = self._extract_details(content)

                result = callback(details)

                # Log result and move to Done
                self._log_execution(action_type, details, result)

            # Move to Done folder
            done_path = self.done_dir / filepath.name
            shutil.move(str(filepath), str(done_path))

        except Exception as e:
            print(f"Error processing approved file: {e}")

    def _extract_action_type(self, filename: str, content: str) -> str:
        """Extract action type from filename or content."""
        # Try to get from filename (e.g., PAYMENT_xxx.md -> payment)
        parts = filename.split('_')
        if parts:
            return parts[0].lower()
        return 'unknown'

    def _extract_details(self, content: str) -> Dict[str, Any]:
        """Extract JSON details from approval file content."""
        try:
            # Find JSON block in content
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
        except:
            pass
        return {}

    def _log_execution(
        self,
        action_type: str,
        details: Dict[str, Any],
        result: Any
    ) -> None:
        """Log the executed action."""
        logs_dir = self.vault_path / 'Logs'
        logs_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now().strftime('%Y-%m-%d')
        log_file = logs_dir / f'{today}.json'

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_type': action_type,
            'details': details,
            'result': str(result),
            'approval_status': 'approved',
            'approved_by': 'human'
        }

        logs = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)

        logs.append(log_entry)

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)


class ApprovalManager:
    """Manages the approval workflow."""

    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self.action_callbacks = {}
        self.observer = None

    def register_action(self, action_type: str, callback: Callable) -> None:
        """Register a callback for an action type."""
        self.action_callbacks[action_type] = callback

    def request_approval(
        self,
        action_type: str,
        details: Dict[str, Any],
        expires_hours: int = 24
    ) -> Path:
        """Create an approval request."""
        request = ApprovalRequest(
            action_type=action_type,
            details=details,
            vault_path=self.vault_path,
            expires_hours=expires_hours
        )
        return request.create_approval_file()

    def start_watching(self) -> None:
        """Start watching for approved files."""
        handler = ApprovalHandler(self.vault_path, self.action_callbacks)
        self.observer = Observer()

        approved_dir = Path(self.vault_path) / 'Approved'
        self.observer.schedule(handler, str(approved_dir), recursive=False)
        self.observer.start()

    def stop_watching(self) -> None:
        """Stop watching."""
        if self.observer:
            self.observer.stop()
            self.observer.join()


# Example usage
if __name__ == '__main__':
    def handle_payment(details):
        print(f"Processing payment: {details}")
        return "Payment processed"

    def handle_email(details):
        print(f"Sending email: {details}")
        return "Email sent"

    manager = ApprovalManager('./AI_Employee_Vault')
    manager.register_action('payment', handle_payment)
    manager.register_action('email', handle_email)

    # Create a test approval request
    manager.request_approval('payment', {
        'amount': 150.00,
        'recipient': 'vendor@example.com',
        'description': 'Invoice #123'
    })

    # Start watching
    manager.start_watching()

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.stop_watching()
```

### 2.5 Build Orchestrator

**File: `orchestrator.py`**

```python
"""
Main Orchestrator
Coordinates all watchers, manages scheduling, and handles the main loop.
"""

import os
import sys
import json
import time
import signal
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, Future

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from watchers.filesystem_watcher import FileSystemWatcher
from watchers.gmail_watcher import GmailWatcher
from utils.approval_handler import ApprovalManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('orchestrator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Orchestrator')


class Orchestrator:
    """Main orchestrator for the AI Employee system."""

    def __init__(self, config_path: str = 'config/orchestrator.json'):
        self.config = self._load_config(config_path)
        self.vault_path = self.config.get('vault_path', './AI_Employee_Vault')
        self.watchers: Dict[str, any] = {}
        self.futures: Dict[str, Future] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.approval_manager = ApprovalManager(self.vault_path)
        self.is_running = False

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self, config_path: str) -> dict:
        """Load configuration from file."""
        config_file = Path(config_path)

        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)

        # Default configuration
        return {
            'vault_path': './AI_Employee_Vault',
            'watchers': {
                'filesystem': {
                    'enabled': True,
                    'watch_folder': './AI_Employee_Vault/Drop',
                    'check_interval': 5
                },
                'gmail': {
                    'enabled': False,
                    'credentials_path': './config/gmail_credentials.json',
                    'check_interval': 120
                }
            },
            'claude_code': {
                'auto_process': True,
                'process_interval': 300
            }
        }

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received")
        self.stop()

    def initialize_watchers(self) -> None:
        """Initialize all configured watchers."""
        watcher_config = self.config.get('watchers', {})

        # File System Watcher
        if watcher_config.get('filesystem', {}).get('enabled', False):
            fs_config = watcher_config['filesystem']
            self.watchers['filesystem'] = FileSystemWatcher(
                vault_path=self.vault_path,
                watch_folder=fs_config.get('watch_folder', f'{self.vault_path}/Drop'),
                check_interval=fs_config.get('check_interval', 5)
            )
            logger.info("FileSystem watcher initialized")

        # Gmail Watcher
        if watcher_config.get('gmail', {}).get('enabled', False):
            gmail_config = watcher_config['gmail']
            try:
                self.watchers['gmail'] = GmailWatcher(
                    vault_path=self.vault_path,
                    credentials_path=gmail_config.get('credentials_path'),
                    check_interval=gmail_config.get('check_interval', 120)
                )
                logger.info("Gmail watcher initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gmail watcher: {e}")

    def start_watchers(self) -> None:
        """Start all watchers in separate threads."""
        for name, watcher in self.watchers.items():
            logger.info(f"Starting {name} watcher")
            future = self.executor.submit(watcher.run)
            self.futures[name] = future

    def setup_approval_callbacks(self) -> None:
        """Setup callbacks for approved actions."""

        def handle_email_send(details):
            """Handle approved email send."""
            logger.info(f"Sending approved email to {details.get('to')}")
            # Trigger MCP email send
            return self._trigger_mcp_action('email', 'send_email', details)

        def handle_payment(details):
            """Handle approved payment."""
            logger.info(f"Processing approved payment: {details.get('amount')}")
            # Trigger payment action
            return "Payment processed"

        self.approval_manager.register_action('email', handle_email_send)
        self.approval_manager.register_action('payment', handle_payment)

    def _trigger_mcp_action(
        self,
        server: str,
        tool: str,
        args: dict
    ) -> str:
        """Trigger an MCP action via Claude Code."""
        # This would integrate with Claude Code's MCP system
        logger.info(f"MCP Action: {server}/{tool} with args: {args}")
        return f"MCP action {tool} triggered"

    def process_needs_action(self) -> None:
        """Trigger Claude Code to process Needs_Action folder."""
        needs_action = Path(self.vault_path) / 'Needs_Action'

        # Count pending items
        pending_items = list(needs_action.glob('*.md'))

        if pending_items:
            logger.info(f"Found {len(pending_items)} items to process")

            # Trigger Claude Code (this is a simplified version)
            # In production, you'd use Claude Code's programmatic API
            prompt = f"""
            Process all items in /Needs_Action folder.
            Follow rules in Company_Handbook.md.
            Create plans in /Plans folder.
            Request approval for sensitive actions.
            Update Dashboard.md when done.
            """

            # Log the processing request
            self._log_action('process_request', {
                'items_count': len(pending_items),
                'items': [str(p.name) for p in pending_items]
            })

    def _log_action(self, action_type: str, details: dict) -> None:
        """Log orchestrator action."""
        logs_dir = Path(self.vault_path) / 'Logs'
        logs_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now().strftime('%Y-%m-%d')
        log_file = logs_dir / f'{today}.json'

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'actor': 'orchestrator',
            'action_type': action_type,
            'details': details
        }

        logs = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                logs = json.load(f)

        logs.append(log_entry)

        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2)

    def update_dashboard(self) -> None:
        """Update the dashboard with current status."""
        dashboard_path = Path(self.vault_path) / 'Dashboard.md'

        # Count items in each folder
        needs_action = len(list((Path(self.vault_path) / 'Needs_Action').glob('*.md')))
        pending_approval = len(list((Path(self.vault_path) / 'Pending_Approval').glob('*.md')))
        done_today = len(list((Path(self.vault_path) / 'Done').glob(f'*{datetime.now().strftime("%Y%m%d")}*.md')))

        # Read existing dashboard
        content = dashboard_path.read_text(encoding='utf-8') if dashboard_path.exists() else ''

        # Update status section (simplified)
        status_update = f"""
## System Status (Auto-Updated)
- **Last Update**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Active Watchers**: {len(self.watchers)}
- **Pending Actions**: {needs_action}
- **Awaiting Approval**: {pending_approval}
- **Completed Today**: {done_today}
"""

        # Append or update status
        if '## System Status' in content:
            # Replace existing status section
            import re
            content = re.sub(
                r'## System Status.*?(?=\n## |\Z)',
                status_update,
                content,
                flags=re.DOTALL
            )
        else:
            content = status_update + '\n' + content

        dashboard_path.write_text(content, encoding='utf-8')

    def start(self) -> None:
        """Start the orchestrator."""
        logger.info("Starting AI Employee Orchestrator")
        self.is_running = True

        # Initialize components
        self.initialize_watchers()
        self.setup_approval_callbacks()

        # Start watchers
        self.start_watchers()

        # Start approval watcher
        self.approval_manager.start_watching()

        # Main loop
        process_interval = self.config.get('claude_code', {}).get('process_interval', 300)
        last_process_time = 0

        while self.is_running:
            try:
                current_time = time.time()

                # Process needs_action periodically
                if current_time - last_process_time > process_interval:
                    self.process_needs_action()
                    self.update_dashboard()
                    last_process_time = current_time

                # Check watcher health
                for name, future in self.futures.items():
                    if future.done():
                        exc = future.exception()
                        if exc:
                            logger.error(f"Watcher {name} failed: {exc}")
                            # Restart watcher
                            if name in self.watchers:
                                logger.info(f"Restarting {name} watcher")
                                self.futures[name] = self.executor.submit(
                                    self.watchers[name].run
                                )

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")

    def stop(self) -> None:
        """Stop the orchestrator."""
        logger.info("Stopping AI Employee Orchestrator")
        self.is_running = False

        # Stop watchers
        for name, watcher in self.watchers.items():
            if hasattr(watcher, 'stop'):
                watcher.stop()

        # Stop approval manager
        self.approval_manager.stop_watching()

        # Shutdown executor
        self.executor.shutdown(wait=True)

        logger.info("Orchestrator stopped")


# Entry point
if __name__ == '__main__':
    orchestrator = Orchestrator()
    orchestrator.start()
```

### 2.6 Create Scheduling Configuration

**For Windows - Task Scheduler:**

Create `scripts/schedule_windows.ps1`:

```powershell
# Create scheduled task for daily briefing
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\path\to\daily_briefing.py"
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable

Register-ScheduledTask -TaskName "AI_Employee_Daily_Briefing" -Action $action -Trigger $trigger -Settings $settings
```

**For Linux/Mac - Cron:**

```bash
# Edit crontab
crontab -e

# Add daily briefing at 8 AM
0 8 * * * /usr/bin/python3 /path/to/daily_briefing.py

# Add weekly audit on Sunday at 8 PM
0 20 * * 0 /usr/bin/python3 /path/to/weekly_audit.py
```

---

## Phase 3: Gold Tier - Autonomous Employee

**Goal**: Full integration + Odoo + CEO Briefing + Ralph Wiggum loop

### Checklist

- [ ] **3.1** Integrate social media (LinkedIn, Twitter, Facebook, Instagram)
- [ ] **3.2** Set up Odoo Community (self-hosted)
- [ ] **3.3** Build Odoo MCP Server
- [ ] **3.4** Implement weekly business audit
- [ ] **3.5** Create CEO briefing generator
- [ ] **3.6** Implement Ralph Wiggum loop
- [ ] **3.7** Add error recovery and graceful degradation
- [ ] **3.8** Implement comprehensive audit logging

### 3.1 LinkedIn Integration

**File: `src/watchers/linkedin_watcher.py`**

```python
"""
LinkedIn Watcher and Poster
Uses Playwright for browser automation.
"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright
from .base_watcher import BaseWatcher


class LinkedInManager(BaseWatcher):
    """Manage LinkedIn interactions."""

    def __init__(
        self,
        vault_path: str,
        session_path: str,
        check_interval: int = 300
    ):
        super().__init__(vault_path, check_interval, "LinkedInManager")
        self.session_path = Path(session_path)
        self.session_path.mkdir(parents=True, exist_ok=True)

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """Check for LinkedIn notifications/messages."""
        # Implementation for checking LinkedIn
        return []

    def create_action_file(self, item: Dict[str, Any]) -> Path:
        """Create action file for LinkedIn item."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        action_path = self.needs_action / f'LINKEDIN_{timestamp}.md'
        # Create action file content
        return action_path

    def create_post(
        self,
        content: str,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Create a LinkedIn post."""
        if dry_run:
            return {
                'status': 'draft',
                'content': content,
                'message': 'Post created as draft (dry run)'
            }

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch_persistent_context(
                    str(self.session_path),
                    headless=False
                )

                page = browser.pages[0] if browser.pages else browser.new_page()
                page.goto('https://www.linkedin.com/feed/')

                # Wait for page load
                page.wait_for_selector('[data-testid="share-box"]', timeout=30000)

                # Click on share box
                page.click('[data-testid="share-box"]')
                page.wait_for_timeout(1000)

                # Type content
                page.fill('[data-testid="share-box-input"]', content)

                # Click post (commented out for safety)
                # page.click('[data-testid="share-actions__primary-action"]')

                browser.close()

                return {
                    'status': 'success',
                    'content': content,
                    'message': 'Post created successfully'
                }

        except Exception as e:
            return {
                'status': 'error',
                'content': content,
                'message': str(e)
            }
```

### 3.2 Odoo Integration

**File: `src/mcp_servers/odoo-mcp/odoo_client.py`**

```python
"""
Odoo JSON-RPC Client
Connects to Odoo Community Edition for accounting integration.
"""

import json
import random
import requests
from typing import Any, Dict, List, Optional


class OdooClient:
    """Client for Odoo JSON-RPC API."""

    def __init__(
        self,
        url: str,
        db: str,
        username: str,
        password: str
    ):
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.uid = None

        # Authenticate
        self._authenticate()

    def _json_rpc(
        self,
        endpoint: str,
        method: str,
        params: Dict[str, Any]
    ) -> Any:
        """Make a JSON-RPC call."""
        payload = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'id': random.randint(1, 1000000000)
        }

        response = requests.post(
            f'{self.url}{endpoint}',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )

        result = response.json()

        if 'error' in result:
            raise Exception(result['error']['data']['message'])

        return result.get('result')

    def _authenticate(self) -> None:
        """Authenticate with Odoo."""
        self.uid = self._json_rpc(
            '/web/session/authenticate',
            'call',
            {
                'db': self.db,
                'login': self.username,
                'password': self.password
            }
        ).get('uid')

        if not self.uid:
            raise Exception('Authentication failed')

    def search_read(
        self,
        model: str,
        domain: List = None,
        fields: List[str] = None,
        limit: int = None
    ) -> List[Dict]:
        """Search and read records."""
        return self._json_rpc(
            '/web/dataset/call_kw',
            'call',
            {
                'model': model,
                'method': 'search_read',
                'args': [domain or []],
                'kwargs': {
                    'fields': fields or [],
                    'limit': limit
                }
            }
        )

    def create(self, model: str, values: Dict) -> int:
        """Create a record."""
        return self._json_rpc(
            '/web/dataset/call_kw',
            'call',
            {
                'model': model,
                'method': 'create',
                'args': [values],
                'kwargs': {}
            }
        )

    # Accounting specific methods

    def get_invoices(
        self,
        state: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get invoices."""
        domain = [('move_type', 'in', ['out_invoice', 'out_refund'])]
        if state:
            domain.append(('state', '=', state))

        return self.search_read(
            'account.move',
            domain=domain,
            fields=['name', 'partner_id', 'amount_total', 'state', 'invoice_date', 'invoice_date_due'],
            limit=limit
        )

    def get_payments(self, limit: int = 50) -> List[Dict]:
        """Get payments."""
        return self.search_read(
            'account.payment',
            fields=['name', 'partner_id', 'amount', 'state', 'date'],
            limit=limit
        )

    def get_bank_balance(self) -> float:
        """Get current bank balance."""
        accounts = self.search_read(
            'account.account',
            domain=[('account_type', '=', 'asset_cash')],
            fields=['name', 'current_balance']
        )

        return sum(acc.get('current_balance', 0) for acc in accounts)

    def create_invoice_draft(
        self,
        partner_id: int,
        lines: List[Dict],
        invoice_date: str = None
    ) -> int:
        """Create a draft invoice."""
        invoice_lines = []
        for line in lines:
            invoice_lines.append((0, 0, {
                'name': line['description'],
                'quantity': line.get('quantity', 1),
                'price_unit': line['price']
            }))

        return self.create('account.move', {
            'move_type': 'out_invoice',
            'partner_id': partner_id,
            'invoice_date': invoice_date,
            'invoice_line_ids': invoice_lines
        })


# Example usage
if __name__ == '__main__':
    client = OdooClient(
        url='http://localhost:8069',
        db='mycompany',
        username='admin',
        password='admin'
    )

    # Get recent invoices
    invoices = client.get_invoices(limit=10)
    print(f"Found {len(invoices)} invoices")

    # Get bank balance
    balance = client.get_bank_balance()
    print(f"Bank balance: ${balance:,.2f}")
```

### 3.3 CEO Briefing Generator

**File: `src/skills/ceo_briefing.py`**

```python
"""
CEO Briefing Generator
Creates weekly "Monday Morning CEO Briefing" reports.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List


class CEOBriefingGenerator:
    """Generate CEO briefings from vault data."""

    def __init__(self, vault_path: str, odoo_client=None):
        self.vault_path = Path(vault_path)
        self.odoo_client = odoo_client

    def generate_briefing(self) -> str:
        """Generate the CEO briefing."""
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        # Gather data
        revenue_data = self._calculate_revenue(start_date, end_date)
        completed_tasks = self._get_completed_tasks(start_date, end_date)
        bottlenecks = self._identify_bottlenecks(start_date, end_date)
        suggestions = self._generate_suggestions()

        # Generate briefing
        briefing = f'''---
generated: {datetime.now().isoformat()}
period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
---

# Monday Morning CEO Briefing

## Executive Summary
{self._generate_summary(revenue_data, completed_tasks, bottlenecks)}

## Revenue

| Metric | Value |
|--------|-------|
| **This Week** | ${revenue_data.get('week_total', 0):,.2f} |
| **MTD** | ${revenue_data.get('mtd_total', 0):,.2f} |
| **Target Progress** | {revenue_data.get('target_progress', 0):.1f}% |
| **Trend** | {revenue_data.get('trend', 'Stable')} |

### Revenue Breakdown
{self._format_revenue_breakdown(revenue_data.get('breakdown', []))}

## Completed Tasks

{self._format_completed_tasks(completed_tasks)}

## Bottlenecks & Delays

{self._format_bottlenecks(bottlenecks)}

## Proactive Suggestions

{self._format_suggestions(suggestions)}

## Upcoming Deadlines

{self._get_upcoming_deadlines()}

---
*Generated by AI Employee v1.0*
*Review time: ~5 minutes*
'''

        # Save briefing
        briefings_dir = self.vault_path / 'Briefings'
        briefings_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{end_date.strftime('%Y-%m-%d')}_Monday_Briefing.md"
        filepath = briefings_dir / filename
        filepath.write_text(briefing, encoding='utf-8')

        return briefing

    def _calculate_revenue(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate revenue metrics."""
        # Try to get from Odoo if available
        if self.odoo_client:
            try:
                invoices = self.odoo_client.get_invoices(state='posted')
                week_invoices = [
                    inv for inv in invoices
                    if start_date.date() <= datetime.fromisoformat(inv['invoice_date']).date() <= end_date.date()
                ]
                week_total = sum(inv['amount_total'] for inv in week_invoices)

                # MTD calculation
                month_start = end_date.replace(day=1)
                mtd_invoices = [
                    inv for inv in invoices
                    if month_start.date() <= datetime.fromisoformat(inv['invoice_date']).date() <= end_date.date()
                ]
                mtd_total = sum(inv['amount_total'] for inv in mtd_invoices)

                return {
                    'week_total': week_total,
                    'mtd_total': mtd_total,
                    'target_progress': (mtd_total / 10000) * 100,  # Assuming $10k target
                    'trend': 'Up' if week_total > 2000 else 'Stable',
                    'breakdown': week_invoices[:5]
                }
            except Exception as e:
                print(f"Error getting Odoo data: {e}")

        # Fallback to vault data
        return self._get_revenue_from_vault(start_date, end_date)

    def _get_revenue_from_vault(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get revenue data from vault files."""
        accounting_dir = self.vault_path / 'Accounting'

        # This would parse accounting files in the vault
        return {
            'week_total': 0,
            'mtd_total': 0,
            'target_progress': 0,
            'trend': 'Unknown',
            'breakdown': []
        }

    def _get_completed_tasks(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Get completed tasks from Done folder."""
        done_dir = self.vault_path / 'Done'
        tasks = []

        if done_dir.exists():
            for file in done_dir.glob('*.md'):
                # Parse file to get completion date
                try:
                    content = file.read_text(encoding='utf-8')
                    # Extract task info from frontmatter/content
                    tasks.append({
                        'name': file.stem,
                        'completed': file.stat().st_mtime
                    })
                except:
                    pass

        return tasks[:10]  # Return last 10 tasks

    def _identify_bottlenecks(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Identify tasks that took longer than expected."""
        # This would analyze task completion times
        return []

    def _generate_suggestions(self) -> List[Dict]:
        """Generate proactive suggestions."""
        suggestions = []

        # Check for unused subscriptions
        # Check for overdue invoices
        # Check for upcoming renewals

        return suggestions

    def _generate_summary(
        self,
        revenue_data: Dict,
        completed_tasks: List,
        bottlenecks: List
    ) -> str:
        """Generate executive summary."""
        trend = revenue_data.get('trend', 'stable').lower()
        task_count = len(completed_tasks)
        bottleneck_count = len(bottlenecks)

        if trend == 'up' and bottleneck_count == 0:
            return f"Strong week with revenue trending up. {task_count} tasks completed with no significant bottlenecks."
        elif bottleneck_count > 0:
            return f"{task_count} tasks completed. {bottleneck_count} bottleneck(s) identified requiring attention."
        else:
            return f"Steady week with {task_count} tasks completed. Revenue {trend}."

    def _format_revenue_breakdown(self, breakdown: List) -> str:
        """Format revenue breakdown as markdown."""
        if not breakdown:
            return "No revenue breakdown available."

        lines = []
        for item in breakdown:
            lines.append(f"- {item.get('name', 'Unknown')}: ${item.get('amount_total', 0):,.2f}")
        return '\n'.join(lines)

    def _format_completed_tasks(self, tasks: List) -> str:
        """Format completed tasks as markdown."""
        if not tasks:
            return "No tasks completed this week."

        lines = []
        for task in tasks:
            lines.append(f"- [x] {task['name']}")
        return '\n'.join(lines)

    def _format_bottlenecks(self, bottlenecks: List) -> str:
        """Format bottlenecks as markdown."""
        if not bottlenecks:
            return "No significant bottlenecks identified."

        lines = ["| Task | Expected | Actual | Delay |", "|------|----------|--------|-------|"]
        for b in bottlenecks:
            lines.append(f"| {b['task']} | {b['expected']} | {b['actual']} | {b['delay']} |")
        return '\n'.join(lines)

    def _format_suggestions(self, suggestions: List) -> str:
        """Format suggestions as markdown."""
        if not suggestions:
            return "No proactive suggestions at this time."

        lines = []
        for s in suggestions:
            lines.append(f"### {s.get('title', 'Suggestion')}")
            lines.append(s.get('description', ''))
            if s.get('action'):
                lines.append(f"- [ACTION] {s['action']}")
            lines.append('')
        return '\n'.join(lines)

    def _get_upcoming_deadlines(self) -> str:
        """Get upcoming deadlines from vault."""
        # This would parse Business_Goals.md and other files
        return "- Review Business_Goals.md for upcoming deadlines"


# CLI runner
if __name__ == '__main__':
    generator = CEOBriefingGenerator('./AI_Employee_Vault')
    briefing = generator.generate_briefing()
    print(briefing)
```

### 3.4 Ralph Wiggum Loop Implementation

**File: `src/utils/ralph_wiggum.py`**

```python
"""
Ralph Wiggum Loop
Keeps Claude Code working until task is complete.

The pattern:
1. Orchestrator creates state file with prompt
2. Claude works on task
3. Claude tries to exit
4. Stop hook checks: Is task complete?
5. NO → Block exit, re-inject prompt
6. YES → Allow exit
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable


class RalphWiggumLoop:
    """
    Manages persistent Claude Code sessions that loop until completion.
    """

    def __init__(
        self,
        vault_path: str,
        max_iterations: int = 10,
        completion_check: Optional[Callable[[], bool]] = None
    ):
        self.vault_path = Path(vault_path)
        self.max_iterations = max_iterations
        self.completion_check = completion_check
        self.state_file = self.vault_path / '.ralph_state.json'

    def start_loop(
        self,
        prompt: str,
        completion_promise: str = "TASK_COMPLETE"
    ) -> dict:
        """
        Start a Ralph Wiggum loop.

        Args:
            prompt: The task prompt for Claude
            completion_promise: String Claude outputs when done

        Returns:
            Result dictionary with status and iterations
        """
        # Create initial state
        state = {
            'prompt': prompt,
            'completion_promise': completion_promise,
            'started': datetime.now().isoformat(),
            'iterations': 0,
            'status': 'running',
            'outputs': []
        }

        self._save_state(state)

        # Main loop
        while state['iterations'] < self.max_iterations:
            state['iterations'] += 1

            # Run Claude Code with prompt
            result = self._run_claude(prompt, state['iterations'])
            state['outputs'].append(result)

            # Check for completion
            if self._is_complete(result, completion_promise):
                state['status'] = 'completed'
                state['completed'] = datetime.now().isoformat()
                self._save_state(state)
                return state

            # Check custom completion function
            if self.completion_check and self.completion_check():
                state['status'] = 'completed'
                state['completed'] = datetime.now().isoformat()
                self._save_state(state)
                return state

            # Update prompt with previous output context
            prompt = self._update_prompt(prompt, result)
            self._save_state(state)

        # Max iterations reached
        state['status'] = 'max_iterations'
        self._save_state(state)
        return state

    def _run_claude(self, prompt: str, iteration: int) -> str:
        """Run Claude Code with prompt."""
        try:
            # Create temporary prompt file
            prompt_file = self.vault_path / f'.ralph_prompt_{iteration}.md'
            prompt_file.write_text(prompt, encoding='utf-8')

            # Run Claude Code
            # Note: This is simplified - actual implementation would use
            # Claude Code's programmatic API or hooks
            result = subprocess.run(
                ['claude', '--print', '-p', str(prompt_file)],
                capture_output=True,
                text=True,
                cwd=str(self.vault_path),
                timeout=300
            )

            output = result.stdout + result.stderr

            # Cleanup
            prompt_file.unlink(missing_ok=True)

            return output

        except subprocess.TimeoutExpired:
            return "TIMEOUT: Claude Code took too long"
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _is_complete(self, output: str, completion_promise: str) -> bool:
        """Check if task is complete based on output."""
        # Check for completion promise in output
        if completion_promise in output:
            return True

        # Check if task file moved to Done
        done_dir = self.vault_path / 'Done'
        needs_action = self.vault_path / 'Needs_Action'

        # If Needs_Action is empty and Done has new files
        if needs_action.exists() and not any(needs_action.glob('*.md')):
            return True

        return False

    def _update_prompt(self, original_prompt: str, previous_output: str) -> str:
        """Update prompt with context from previous iteration."""
        return f"""
{original_prompt}

---
PREVIOUS ITERATION OUTPUT:
{previous_output[:2000]}  # Truncate to avoid context overflow

---
CONTINUE WORKING ON THE TASK.
If complete, output: <promise>TASK_COMPLETE</promise>
"""

    def _save_state(self, state: dict) -> None:
        """Save state to file."""
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> Optional[dict]:
        """Load state from file."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return None

    def check_completion_by_file_movement(self) -> bool:
        """
        Check if task is complete by checking if task file is in Done.
        This is the "file movement" completion strategy for Gold tier.
        """
        state = self._load_state()
        if not state:
            return False

        # Check if the original task file has been moved to Done
        # This requires tracking which file triggered the loop
        done_dir = self.vault_path / 'Done'

        # For simplicity, check if Needs_Action is empty
        needs_action = self.vault_path / 'Needs_Action'
        return not any(needs_action.glob('*.md'))


# CLI interface
def main():
    import argparse

    parser = argparse.ArgumentParser(description='Ralph Wiggum Loop')
    parser.add_argument('prompt', help='Task prompt for Claude')
    parser.add_argument('--vault', default='./AI_Employee_Vault', help='Vault path')
    parser.add_argument('--max-iterations', type=int, default=10, help='Max iterations')
    parser.add_argument('--completion-promise', default='TASK_COMPLETE', help='Completion string')

    args = parser.parse_args()

    loop = RalphWiggumLoop(args.vault, args.max_iterations)
    result = loop.start_loop(args.prompt, args.completion_promise)

    print(f"Loop completed with status: {result['status']}")
    print(f"Iterations: {result['iterations']}")


if __name__ == '__main__':
    main()
```

### 3.5 Error Recovery & Watchdog

**File: `watchdog.py`**

```python
"""
Watchdog Process
Monitors and restarts critical processes.
"""

import os
import sys
import time
import json
import signal
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('Watchdog')


class ProcessWatchdog:
    """Monitor and restart critical processes."""

    def __init__(self, config_path: str = 'config/watchdog.json'):
        self.config = self._load_config(config_path)
        self.processes: Dict[str, subprocess.Popen] = {}
        self.restart_counts: Dict[str, int] = {}
        self.is_running = False

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self, config_path: str) -> dict:
        """Load configuration."""
        config_file = Path(config_path)

        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)

        return {
            'check_interval': 60,
            'max_restarts': 5,
            'restart_cooldown': 300,
            'processes': {
                'orchestrator': {
                    'command': 'python orchestrator.py',
                    'working_dir': '.',
                    'critical': True
                }
            },
            'notifications': {
                'email': None,
                'slack': None
            }
        }

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Shutdown signal received")
        self.stop()

    def start_process(self, name: str, config: dict) -> Optional[subprocess.Popen]:
        """Start a process."""
        try:
            command = config['command'].split()
            working_dir = config.get('working_dir', '.')

            proc = subprocess.Popen(
                command,
                cwd=working_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            logger.info(f"Started {name} (PID: {proc.pid})")
            return proc

        except Exception as e:
            logger.error(f"Failed to start {name}: {e}")
            return None

    def check_process(self, name: str) -> bool:
        """Check if process is running."""
        if name not in self.processes:
            return False

        proc = self.processes[name]
        return proc.poll() is None

    def restart_process(self, name: str, config: dict) -> bool:
        """Restart a process."""
        # Check restart limits
        self.restart_counts[name] = self.restart_counts.get(name, 0) + 1

        if self.restart_counts[name] > self.config.get('max_restarts', 5):
            logger.error(f"{name} exceeded max restarts, not restarting")
            self._notify(f"CRITICAL: {name} exceeded max restarts")
            return False

        # Kill existing process if still running
        if name in self.processes:
            try:
                self.processes[name].terminate()
                self.processes[name].wait(timeout=5)
            except:
                self.processes[name].kill()

        # Start new process
        proc = self.start_process(name, config)

        if proc:
            self.processes[name] = proc
            self._notify(f"Restarted {name} (restart #{self.restart_counts[name]})")
            return True

        return False

    def _notify(self, message: str) -> None:
        """Send notification."""
        logger.warning(message)

        # Add email/Slack notifications here
        notifications = self.config.get('notifications', {})

        # Email notification
        if notifications.get('email'):
            # Send email notification
            pass

        # Slack notification
        if notifications.get('slack'):
            # Send Slack notification
            pass

    def run(self) -> None:
        """Main watchdog loop."""
        logger.info("Starting Watchdog")
        self.is_running = True

        # Start all configured processes
        for name, config in self.config.get('processes', {}).items():
            proc = self.start_process(name, config)
            if proc:
                self.processes[name] = proc

        # Monitor loop
        check_interval = self.config.get('check_interval', 60)

        while self.is_running:
            for name, config in self.config.get('processes', {}).items():
                if not self.check_process(name):
                    logger.warning(f"{name} is not running")

                    if config.get('critical', False):
                        self.restart_process(name, config)

            time.sleep(check_interval)

    def stop(self) -> None:
        """Stop watchdog and all processes."""
        logger.info("Stopping Watchdog")
        self.is_running = False

        for name, proc in self.processes.items():
            try:
                proc.terminate()
                proc.wait(timeout=5)
                logger.info(f"Stopped {name}")
            except:
                proc.kill()
                logger.warning(f"Killed {name}")


if __name__ == '__main__':
    watchdog = ProcessWatchdog()
    watchdog.run()
```

---

## Phase 4: Platinum Tier - Cloud Deployment

**Goal**: Always-on cloud + local executive + production security

### Checklist

- [ ] **4.1** Set up Cloud VM (Oracle Cloud Free / AWS / Azure)
- [ ] **4.2** Configure Cloud Agent (email triage, social drafts)
- [ ] **4.3** Configure Local Agent (approvals, payments, WhatsApp)
- [ ] **4.4** Implement vault sync (Git or Syncthing)
- [ ] **4.5** Deploy Odoo on cloud with HTTPS
- [ ] **4.6** Implement health monitoring
- [ ] **4.7** Set up claim-by-move rule for multi-agent
- [ ] **4.8** Configure production security

### 4.1 Cloud VM Setup

**Oracle Cloud Free Tier Setup:**

```bash
# Install required software on VM
sudo apt update
sudo apt install -y python3.11 python3-pip nodejs npm git

# Clone your repository
git clone https://github.com/yourusername/ai-employee.git
cd ai-employee

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install PM2 for process management
sudo npm install -g pm2

# Start processes
pm2 start orchestrator.py --interpreter python3 --name ai-employee
pm2 start watchdog.py --interpreter python3 --name watchdog

# Save PM2 config for restart on reboot
pm2 save
pm2 startup
```

### 4.2 Work-Zone Specialization

**File: `config/cloud_agent.json`**

```json
{
  "agent_name": "cloud",
  "capabilities": {
    "email_triage": true,
    "draft_replies": true,
    "social_drafts": true,
    "social_scheduling": true
  },
  "restrictions": {
    "send_emails": false,
    "post_social": false,
    "payments": false,
    "whatsapp": false
  },
  "output_folders": [
    "/Needs_Action/email/",
    "/Plans/email/",
    "/Pending_Approval/email/"
  ]
}
```

**File: `config/local_agent.json`**

```json
{
  "agent_name": "local",
  "capabilities": {
    "approvals": true,
    "send_emails": true,
    "post_social": true,
    "payments": true,
    "whatsapp": true,
    "banking": true
  },
  "owned_folders": [
    "/Approved/",
    "/Pending_Approval/"
  ],
  "dashboard_writer": true
}
```

### 4.3 Vault Sync Configuration

**Using Git (Recommended):**

**File: `scripts/vault_sync.sh`**

```bash
#!/bin/bash
# Vault sync script - runs on both cloud and local

VAULT_PATH="./AI_Employee_Vault"
SYNC_BRANCH="vault-sync"

cd "$VAULT_PATH"

# Pull latest changes
git fetch origin
git merge origin/$SYNC_BRANCH --no-edit

# Add and commit local changes
git add -A
git commit -m "Auto-sync $(date +%Y-%m-%d_%H:%M:%S)" || true

# Push changes
git push origin $SYNC_BRANCH
```

**Add to cron (run every minute):**

```bash
* * * * * /path/to/vault_sync.sh >> /var/log/vault_sync.log 2>&1
```

### 4.4 Health Monitoring

**File: `src/utils/health_monitor.py`**

```python
"""
Health Monitor
Monitors system health and sends alerts.
"""

import os
import time
import json
import psutil
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class HealthMonitor:
    """Monitor system health."""

    def __init__(self, config_path: str = 'config/health.json'):
        self.config = self._load_config(config_path)
        self.alerts_sent: Dict[str, datetime] = {}

    def _load_config(self, config_path: str) -> dict:
        """Load configuration."""
        return {
            'check_interval': 60,
            'thresholds': {
                'cpu_percent': 90,
                'memory_percent': 85,
                'disk_percent': 90
            },
            'alert_cooldown': 300,  # seconds
            'webhook_url': os.getenv('HEALTH_WEBHOOK_URL')
        }

    def check_system_health(self) -> Dict[str, Any]:
        """Check system resource usage."""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'timestamp': datetime.now().isoformat()
        }

    def check_process_health(self, process_names: list) -> Dict[str, bool]:
        """Check if specific processes are running."""
        running = {}
        for proc in psutil.process_iter(['name', 'cmdline']):
            for name in process_names:
                if name in ' '.join(proc.info.get('cmdline', [])):
                    running[name] = True

        for name in process_names:
            if name not in running:
                running[name] = False

        return running

    def check_vault_health(self, vault_path: str) -> Dict[str, Any]:
        """Check vault directory health."""
        vault = Path(vault_path)

        return {
            'exists': vault.exists(),
            'needs_action_count': len(list((vault / 'Needs_Action').glob('*.md'))) if vault.exists() else 0,
            'pending_approval_count': len(list((vault / 'Pending_Approval').glob('*.md'))) if vault.exists() else 0,
            'last_log': self._get_last_log_time(vault)
        }

    def _get_last_log_time(self, vault: Path) -> str:
        """Get timestamp of last log entry."""
        logs_dir = vault / 'Logs'
        if not logs_dir.exists():
            return 'No logs'

        log_files = sorted(logs_dir.glob('*.json'), reverse=True)
        if log_files:
            return log_files[0].stem
        return 'No logs'

    def send_alert(self, alert_type: str, message: str) -> None:
        """Send an alert."""
        # Check cooldown
        if alert_type in self.alerts_sent:
            cooldown = self.config.get('alert_cooldown', 300)
            if (datetime.now() - self.alerts_sent[alert_type]).seconds < cooldown:
                return

        self.alerts_sent[alert_type] = datetime.now()

        webhook_url = self.config.get('webhook_url')
        if webhook_url:
            try:
                requests.post(webhook_url, json={
                    'alert_type': alert_type,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                })
            except:
                pass

        print(f"ALERT [{alert_type}]: {message}")

    def run(self) -> None:
        """Main monitoring loop."""
        while True:
            # Check system health
            system = self.check_system_health()
            thresholds = self.config.get('thresholds', {})

            if system['cpu_percent'] > thresholds.get('cpu_percent', 90):
                self.send_alert('cpu', f"CPU usage high: {system['cpu_percent']}%")

            if system['memory_percent'] > thresholds.get('memory_percent', 85):
                self.send_alert('memory', f"Memory usage high: {system['memory_percent']}%")

            if system['disk_percent'] > thresholds.get('disk_percent', 90):
                self.send_alert('disk', f"Disk usage high: {system['disk_percent']}%")

            time.sleep(self.config.get('check_interval', 60))


if __name__ == '__main__':
    monitor = HealthMonitor()
    monitor.run()
```

---

## Security Implementation

### Environment Variables

**File: `.env.example`**

```bash
# Claude Code
ANTHROPIC_API_KEY=your_api_key_here

# Gmail
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret

# Email SMTP
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_app_password
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587

# Odoo
ODOO_URL=http://localhost:8069
ODOO_DB=mycompany
ODOO_USER=admin
ODOO_PASSWORD=admin

# WhatsApp
WHATSAPP_SESSION_PATH=/secure/path/session

# Monitoring
HEALTH_WEBHOOK_URL=https://hooks.slack.com/services/xxx

# Development
DRY_RUN=true
DEV_MODE=true
```

### .gitignore

**File: `.gitignore`**

```gitignore
# Environment
.env
.env.local
*.env

# Credentials
credentials.json
token.json
*_credentials.json
*.pem
*.key

# Sessions
session/
*_session/
*.session

# Logs (keep structure, ignore content)
AI_Employee_Vault/Logs/*.json

# Python
__pycache__/
*.py[cod]
venv/
.venv/

# Node
node_modules/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# State files
.ralph_state.json
*.pid
```

---

## Testing & Validation

### Test Checklist

**Bronze Tier:**
- [ ] Vault structure created correctly
- [ ] Dashboard.md renders in Obsidian
- [ ] File watcher detects new files
- [ ] Action files created in Needs_Action
- [ ] Claude Code can read/write to vault

**Silver Tier:**
- [ ] Multiple watchers run concurrently
- [ ] MCP server responds to tool calls
- [ ] HITL approval flow works
- [ ] Scheduled tasks execute
- [ ] Orchestrator manages processes

**Gold Tier:**
- [ ] Social media posting works (dry run)
- [ ] Odoo integration retrieves data
- [ ] CEO briefing generates correctly
- [ ] Ralph Wiggum loop completes tasks
- [ ] Error recovery restarts failed processes

**Platinum Tier:**
- [ ] Cloud VM stays online 24/7
- [ ] Vault sync works between cloud/local
- [ ] Work-zone separation enforced
- [ ] Health monitoring sends alerts
- [ ] End-to-end flow: email → cloud draft → local approve → send

---

## Resources & References

### Official Documentation
- Claude Code: https://docs.anthropic.com/claude-code
- MCP Protocol: https://modelcontextprotocol.io
- Obsidian: https://help.obsidian.md
- Odoo API: https://www.odoo.com/documentation/19.0/developer/reference/external_api.html

### Learning Resources
- Agent Factory Textbook: https://agentfactory.panaversity.org
- Claude Code + Obsidian Video: https://youtube.com/watch?v=sCIS05Qt79Y
- Agent Skills Video: https://youtube.com/watch?v=nbqqnl3JdR0

### Weekly Meetings
- Zoom: https://us06web.zoom.us/j/87188707642
- Every Wednesday 10:00 PM
- YouTube: https://youtube.com/@panaversity

### Submission
- Form: https://forms.gle/JR9T1SJq5rmQyGkGA
- Include: GitHub repo, README, demo video (5-10 min), security disclosure

---

## Progress Tracking

### Current Status

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 0: Prerequisites | Not Started | 0% |
| Phase 1: Bronze | Not Started | 0% |
| Phase 2: Silver | Not Started | 0% |
| Phase 3: Gold | Not Started | 0% |
| Phase 4: Platinum | Not Started | 0% |

### Next Steps

1. Complete Phase 0 prerequisites
2. Create Obsidian vault structure
3. Build first file system watcher
4. Test Claude Code integration
5. Progress through remaining phases

---

*Last Updated: {{date}}*
*Target Completion: All Tiers (Platinum)*
