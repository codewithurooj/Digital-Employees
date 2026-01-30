---
name: whatsapp-watcher
description: Monitor WhatsApp Web for important messages matching keywords and create action files in the Obsidian vault. Uses Playwright for browser automation with persistent login. Use this skill when setting up WhatsApp monitoring, configuring keyword triggers, or integrating WhatsApp messages with the AI Employee workflow. Triggers for WhatsApp automation tasks, message monitoring setup, or browser-based communication tracking.
---

# WhatsApp Watcher

Monitor WhatsApp Web for important messages and create action files for the AI Employee workflow.

## Overview

The WhatsApp Watcher uses Playwright browser automation to:
- Monitor WhatsApp Web for unread messages
- Filter messages by keywords (urgent, payment, meeting, etc.)
- Create structured action files in `Needs_Action/` folder
- Maintain persistent login (scan QR once)
- Support contact whitelisting

## Quick Start

### Prerequisites

```bash
# Install Playwright
pip install playwright

# Install Chromium browser
playwright install chromium
```

### First Run (QR Code Authentication)

```bash
# Run with visible browser for QR scan
python -m src.watchers.whatsapp_watcher --vault ./AI_Employee_Vault

# 1. Browser opens WhatsApp Web
# 2. Scan QR code with WhatsApp mobile app
# 3. Session saved automatically for future runs
```

### Subsequent Runs

```bash
# Can run headless after initial login
python -m src.watchers.whatsapp_watcher --vault ./AI_Employee_Vault --headless
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `vault_path` | Required | Path to Obsidian vault |
| `session_path` | `config/whatsapp_session` | Browser session storage |
| `check_interval` | `30` | Seconds between checks |
| `keywords` | See below | Trigger words for action creation |
| `headless` | `False` | Run browser without GUI |
| `contacts_whitelist` | `None` | Only monitor specific contacts |

### Default Keywords

```python
['urgent', 'asap', 'help', 'important', 'invoice',
 'payment', 'deadline', 'meeting', 'call', 'emergency',
 'please respond', 'need']
```

### Custom Keywords

```bash
python -m src.watchers.whatsapp_watcher --vault ./AI_Employee_Vault \
    --keywords urgent important payment invoice meeting
```

## Programmatic Usage

```python
from src.watchers import WhatsAppWatcher

watcher = WhatsAppWatcher(
    vault_path='./AI_Employee_Vault',
    session_path='./config/whatsapp_session',
    check_interval=30,
    keywords=['urgent', 'payment', 'meeting'],
    contacts_whitelist=['Boss', 'Client Name'],  # Optional
    headless=False  # Set True after initial login
)
watcher.run()
```

## Action File Format

```markdown
---
type: whatsapp
message_id: "contact_hash_timestamp"
contact: "John Doe"
preview: "Hey, urgent meeting needed..."
unread_count: 3
matched_keywords: ["urgent", "meeting"]
priority: "high"
status: pending
requires_approval: false
---

# WhatsApp: John Doe

## Message Details
| Field | Value |
|-------|-------|
| **From** | John Doe |
| **Unread** | 3 message(s) |
| **Priority** | high |
| **Keywords** | urgent, meeting |

## Recent Conversation
```
← Hey, urgent meeting needed
→ Sure, when?
← Can we do 3pm?
```

## Suggested Actions
- [ ] Respond promptly (high priority)
- [ ] Check calendar availability
...
```

## Priority Classification

| Priority | Keywords |
|----------|----------|
| **High** | urgent, asap, emergency, help, important |
| **Medium** | meeting, call, deadline, payment, invoice |
| **Low** | Default for other keywords |

## Approval Rules

Messages require human approval when containing:
- `payment`, `invoice`, `contract`, `money`, `transfer`

## Integration with Orchestrator

```python
from orchestrator import Orchestrator
from src.watchers import WhatsAppWatcher

orch = Orchestrator('./AI_Employee_Vault')
orch.add_watcher('whatsapp', WhatsAppWatcher(
    vault_path='./AI_Employee_Vault',
    keywords=['urgent', 'payment', 'meeting']
))
orch.run()
```

## Session Management

### Session Storage

```
config/whatsapp_session/
├── Default/                 # Chromium profile data
├── Cookies                  # Login cookies
└── Local Storage/          # WhatsApp session
```

### Re-authenticate

```bash
# Delete session and re-scan QR
rm -rf config/whatsapp_session
python -m src.watchers.whatsapp_watcher --vault ./AI_Employee_Vault
```

## Browser Options

| Option | Purpose |
|--------|---------|
| `--headless` | Run without visible browser (after initial login) |
| `--interval 60` | Check every 60 seconds |
| `--session ./custom/path` | Custom session storage location |

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ImportError: Playwright not installed` | Run: `pip install playwright && playwright install chromium` |
| QR code not appearing | Delete session folder and restart |
| Session expired | Delete session folder and re-authenticate |
| Browser crashes | Ensure enough memory, try `--no-headless` |
| Messages not detected | WhatsApp Web UI may have changed - check selectors |
| Slow performance | Increase `check_interval` to reduce load |

## Important Notes

1. **WhatsApp Terms of Service**: This tool is for personal use only. Be aware of WhatsApp's automation policies.

2. **Session Persistence**: After initial QR scan, the session persists. Run headless for unattended operation.

3. **Contact Whitelist**: Use `contacts_whitelist` to limit monitoring to specific contacts.

4. **Keyword Matching**: Keywords are case-insensitive and match anywhere in message preview.

## Setup Guide

See [references/playwright-setup.md](references/playwright-setup.md) for detailed Playwright installation and configuration.
