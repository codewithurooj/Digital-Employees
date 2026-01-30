---
name: gmail-watcher
description: Monitor Gmail inbox for important/unread emails and create action files in the Obsidian vault. Use this skill when you need to poll Gmail for new emails, extract email content, determine priority, and create structured action files for the AI Employee workflow. Triggers when processing email tasks, setting up email monitoring, or integrating Gmail with the vault system.
---

# Gmail Watcher

Monitor Gmail inbox and create action files for the AI Employee workflow.

## Overview

The Gmail Watcher polls Gmail for important/unread emails and creates structured action files in `Needs_Action/` folder with:
- Email metadata (sender, subject, date)
- Priority classification (high/medium/low)
- Category detection (financial, meeting, support, etc.)
- Suggested actions based on content
- Draft response template

## Quick Start

### Prerequisites

1. Google Cloud Project with Gmail API enabled
2. OAuth 2.0 credentials (Desktop app type)
3. Python packages: `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`

### Run the Watcher

```bash
# Basic usage
python -m src.watchers.gmail_watcher --vault ./AI_Employee_Vault

# With custom query
python -m src.watchers.gmail_watcher --vault ./AI_Employee_Vault --query "is:unread"

# Custom interval (seconds)
python -m src.watchers.gmail_watcher --vault ./AI_Employee_Vault --interval 60
```

### Programmatic Usage

```python
from src.watchers import GmailWatcher

watcher = GmailWatcher(
    vault_path='./AI_Employee_Vault',
    credentials_path='./config/gmail_credentials.json',
    query='is:unread is:important',
    check_interval=120
)
watcher.run()
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `vault_path` | Required | Path to Obsidian vault |
| `credentials_path` | Required | Path to Gmail API credentials JSON |
| `token_path` | `config/gmail_token.json` | OAuth token storage |
| `query` | `is:unread is:important` | Gmail search query |
| `check_interval` | `120` | Seconds between checks |
| `max_results` | `10` | Max emails per check |

## Gmail Search Queries

Common queries for filtering emails:

```
is:unread is:important     # Unread important emails (default)
is:unread                  # All unread emails
from:boss@company.com      # From specific sender
subject:urgent             # Subject contains "urgent"
has:attachment             # Emails with attachments
after:2024/01/01          # After specific date
label:inbox is:unread     # Unread in inbox only
```

## Action File Format

Created files follow this structure:

```markdown
---
type: email
message_id: "abc123"
from: "sender@example.com"
subject: "Meeting Tomorrow"
priority: "high"
category: "meeting"
status: pending
requires_approval: false
---

# Email: Meeting Tomorrow

## Details
| Field | Value |
|-------|-------|
| From | sender@example.com |
| Date | 2024-01-15 10:30:00 |

## Preview
> Email snippet...

## Suggested Actions
- [ ] Review email content
- [ ] Check calendar availability
...
```

## Priority Classification

| Priority | Triggers |
|----------|----------|
| **High** | Keywords: urgent, asap, important, deadline, critical; Labels: IMPORTANT, STARRED |
| **Medium** | Keywords: follow up, reminder, update, review, feedback |
| **Low** | Default for other emails |

## Category Detection

| Category | Triggers |
|----------|----------|
| `financial` | invoice, payment, receipt, billing, transaction |
| `meeting` | meeting, calendar, schedule, appointment, call |
| `support` | support, help, issue, problem, complaint |
| `marketing` | CATEGORY_PROMOTIONS label |
| `social` | CATEGORY_SOCIAL label |
| `general` | Default |

## Approval Rules

Emails require human approval (`requires_approval: true`) when containing:
- Legal terms: contract, agreement, legal, confidential
- Financial terms: payment, invoice, wire transfer
- Sensitive: complaint, dispute, lawsuit, termination, resignation

## Integration with Orchestrator

```python
from orchestrator import Orchestrator

orch = Orchestrator('./AI_Employee_Vault')
orch.add_watcher('gmail', GmailWatcher(
    vault_path='./AI_Employee_Vault',
    credentials_path='./config/gmail_credentials.json'
))
orch.run()
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ImportError: Gmail API libraries not installed` | Run: `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib` |
| `FileNotFoundError: Gmail credentials not found` | Download credentials from Google Cloud Console |
| `Token expired` | Delete `gmail_token.json` and re-authenticate |
| `No emails returned` | Check query syntax, verify emails exist matching criteria |

## Setup Guide

See [references/gmail-api-setup.md](references/gmail-api-setup.md) for detailed Google Cloud setup instructions.
