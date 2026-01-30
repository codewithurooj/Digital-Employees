# Platinum Tier Demo Flow

**Purpose**: End-to-end demonstration of Cloud/Local handoff for the AI Employee system.

---

## Architecture Overview

```
┌─────────────────────────┐                    ┌─────────────────────────┐
│     Cloud Agent (24/7)  │                    │   Local Agent (on-demand)│
│                         │                    │                         │
│  1. Gmail Watcher       │    Git Sync        │  4. Pull updates        │
│  2. Email Triage        │ ◄────────────────► │  5. Review approvals    │
│  3. Create drafts       │    (every 30-60s)  │  6. Execute actions     │
│     → Pending_Approval/ │                    │     → Send emails       │
│                         │                    │     → Publish posts     │
│  Work Zone: CLOUD       │                    │  Work Zone: LOCAL       │
│  (draft-only)           │                    │  (full access)          │
└─────────────────────────┘                    └─────────────────────────┘
```

---

## Demo Scenario

### Scenario: Client Email → Draft Response → Approval → Send

**Actors**: Cloud agent (automated), Human (reviewer), Local agent (executor)

### Step 1: Email Arrives (Cloud Agent)

An email arrives from `client@acmecorp.com`:

> Subject: Invoice Request - January Consulting
> Body: Could you please send us the invoice for January? 40 hours at $150/hour.

The cloud agent's Gmail watcher detects the email and creates an action file in `Needs_Action/email/`.

### Step 2: Email Triage (Cloud Agent)

The EmailTriageSkill categorizes the email:
- **Priority**: Normal (no urgent keywords)
- **Action**: Create draft response

A draft file is written to `Pending_Approval/email/email_triage_20260130_100000_demo_001.md`.

### Step 3: Draft Invoice (Cloud Agent)

The CloudOdooMCP creates a draft invoice:
- **Customer**: Acme Corp
- **Line**: 40 hours × $150 = $6,000
- **Status**: Pending Approval

Files created:
- `Accounting/Invoices/DRAFT-20260130100000.md`
- `Pending_Approval/accounting/approve_DRAFT-20260130100000.md`

### Step 4: Git Sync (Automatic)

Cloud agent pushes changes to the shared vault repository. Sync happens every 30-60 seconds.

### Step 5: Local Agent Pulls (Local)

Local agent pulls latest changes and displays pending approvals:
- 1 email draft awaiting review
- 1 invoice draft awaiting approval

### Step 6: Human Reviews (Human)

The human reviews in Obsidian:
1. Opens `Pending_Approval/email/...` - reviews draft response
2. Opens `Pending_Approval/accounting/...` - reviews invoice
3. Moves approved files to `Approved/`

### Step 7: Local Agent Executes (Local)

The local agent detects approved files and:
1. Sends the email via Gmail API (`@requires_local` allows it)
2. Posts the invoice to Odoo (`@requires_local` allows it)
3. Moves files to `Done/`
4. Pushes changes back via Git

### Step 8: Verification

- Email sent and logged in `Logs/`
- Invoice posted to Odoo
- Dashboard updated
- Cloud agent sees completed items on next sync

---

## Running the Demo

### Prerequisites

1. Both agents configured (see `specs/002-platinum-tier/quickstart.md`)
2. Sample email placed in vault

### Quick Start

```bash
# Terminal 1: Start cloud agent (dry-run mode for demo)
python -m src.cloud --vault ./AI_Employee_Vault

# Terminal 2: Start local agent (dry-run mode for demo)
python -m src.local --vault ./AI_Employee_Vault

# Place sample email in the vault
cp deploy/demo/sample_email.md AI_Employee_Vault/Needs_Action/email/
```

### What to Watch

1. **Cloud terminal**: Shows email triage and draft creation
2. **Vault folders**: `Pending_Approval/` populates with drafts
3. **Local terminal**: Shows approval processing
4. **Health/status.md**: Shows system health

---

## Key Concepts Demonstrated

| Concept | How It's Shown |
|---------|----------------|
| Work-Zone Enforcement | Cloud agent creates drafts but cannot send |
| Git-Based Sync | Changes flow between agents via Git |
| Human-in-the-Loop | Approvals processed by human in Obsidian |
| Claim-by-Move | Tasks claimed by moving to In_Progress/ |
| Health Monitoring | Health/status.md shows real-time metrics |
| Audit Trail | All actions logged in Logs/ folder |

---

## Test Coverage

Run the automated demo tests:

```bash
python -m pytest tests/integration/test_platinum_demo.py -v
```

This validates all demo scenarios without requiring external services.
