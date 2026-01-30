# Data Model: Platinum Tier - Always-On Cloud + Local Executive

**Feature**: Platinum Tier
**Date**: 2026-01-28
**Status**: Complete

## Overview

This document defines the new and modified data entities for Platinum Tier features. All entities are stored as markdown files with YAML frontmatter in the Obsidian vault, consistent with Gold Tier patterns. New entities focus on distributed agent coordination, vault synchronization, and health monitoring.

---

## New Entities

### 1. AgentIdentity

**Purpose**: Identifies which agent (cloud or local) is performing operations.

**Storage**: Runtime configuration, environment variable AGENT_ID

```yaml
# Schema
AgentIdentity:
  agent_id: string            # 'cloud' | 'local'
  work_zone: string           # 'cloud' | 'local' (determines permissions)
  hostname: string            # VM/machine hostname
  started_at: datetime        # Agent start timestamp
  version: string             # Code version/commit hash
  capabilities:               # What this agent can do
    - read_vault
    - write_needs_action
    - write_drafts
    - sync_git
    # Local-only capabilities
    - execute_approval        # (local only)
    - send_email              # (local only)
    - post_social             # (local only)
    - process_payment         # (local only)
    - whatsapp_operations     # (local only)

  # Runtime state
  last_heartbeat: datetime    # Last activity timestamp
  active_tasks: integer       # Currently processing
  error_count: integer        # Consecutive errors
```

**Validation Rules**:
- `agent_id` must be 'cloud' or 'local'
- `work_zone` must match `agent_id`
- `capabilities` enforced by WorkZone decorator

---

### 2. TaskClaim

**Purpose**: Records task ownership via claim-by-move protocol.

**Storage**: `AI_Employee_Vault/In_Progress/{agent_id}/{original_filename}.md`

```yaml
---
# YAML Frontmatter (added when claimed)
type: task_claim
original_location: /Needs_Action/email/TASK_20260128_001.md
claimed_by: cloud
claimed_at: 2026-01-28T10:30:00Z
claim_expires: 2026-01-28T10:45:00Z    # 15 min timeout
status: in_progress                     # in_progress | completed | released | expired

# Original task frontmatter preserved below
original_type: email_triage
priority: high
# ... rest of original frontmatter
---

# Task: Email Triage - Client Inquiry

## Claim Info

| Field | Value |
|-------|-------|
| Claimed By | cloud |
| Claimed At | 2026-01-28 10:30 AM |
| Expires | 2026-01-28 10:45 AM |
| Original Location | /Needs_Action/email/TASK_20260128_001.md |

---

## Original Task Content

[Original task content follows here]
```

**Validation Rules**:
- `claimed_by` must be valid agent_id
- `claim_expires` default 15 minutes from claimed_at
- File must not exist at destination (first mover wins)
- On completion: move to /Done or /Pending_Approval
- On release: move back to original location
- On expire: auto-release by other agent

**Claim-by-Move Protocol**:
```
1. Agent A detects task in /Needs_Action/email/TASK_001.md
2. Agent A does: git pull (sync first)
3. Agent A attempts: mv /Needs_Action/email/TASK_001.md /In_Progress/cloud/TASK_001.md
4. Agent A does: git add, commit, push
5. If push succeeds: Agent A owns task
6. If push fails (conflict): Agent B already claimed; Agent A abandons
```

---

### 3. SyncState

**Purpose**: Tracks Git synchronization status and history.

**Storage**: `AI_Employee_Vault/Health/sync_state.json`

```json
{
  "agent_id": "cloud",
  "last_pull": {
    "timestamp": "2026-01-28T10:29:30Z",
    "commit_hash": "a1b2c3d4",
    "files_changed": 3,
    "conflicts": []
  },
  "last_push": {
    "timestamp": "2026-01-28T10:30:45Z",
    "commit_hash": "e5f6g7h8",
    "files_added": 2,
    "message": "cloud: Drafted email reply to Acme Corp"
  },
  "sync_interval_seconds": 30,
  "consecutive_failures": 0,
  "total_syncs_today": 145,
  "conflicts_resolved_today": 0,
  "pending_changes": [],
  "remote_url": "git@github.com:user/AI_Employee_Vault.git",
  "branch": "main"
}
```

**Validation Rules**:
- `sync_interval_seconds` minimum 10, maximum 300
- `consecutive_failures` triggers alert at 5
- `pending_changes` cleared on successful push

---

### 4. HealthStatus

**Purpose**: Records cloud agent health metrics and incidents.

**Storage**: `AI_Employee_Vault/Health/status.md`

```yaml
---
type: health_status
agent_id: cloud
last_check: 2026-01-28T10:30:00Z
overall_status: healthy                # healthy | degraded | critical
check_interval: 60

processes:
  cloud-orchestrator:
    status: running
    pid: 12345
    uptime_seconds: 86400
    restarts_today: 0
    memory_mb: 256
    cpu_percent: 2.5
  health-monitor:
    status: running
    pid: 12346
    uptime_seconds: 86400
    restarts_today: 0

apis:
  gmail:
    status: connected
    last_successful: 2026-01-28T10:29:00Z
    latency_ms: 150
    errors_1h: 0
  odoo:
    status: connected
    last_successful: 2026-01-28T10:28:00Z
    latency_ms: 50
    errors_1h: 0

resources:
  cpu_percent: 15
  memory_percent: 45
  disk_percent: 32
  network_in_mb: 12
  network_out_mb: 5

thresholds:
  cpu_warning: 70
  cpu_critical: 90
  memory_warning: 80
  memory_critical: 95
  disk_warning: 85
  disk_critical: 95

incidents_today: []
last_incident: null
uptime_percent_30d: 99.7
---

# Cloud Agent Health Status

> Last Check: 2026-01-28 10:30 AM

## Overall Status: 🟢 Healthy

## Processes

| Process | Status | Uptime | Memory | CPU |
|---------|--------|--------|--------|-----|
| cloud-orchestrator | 🟢 Running | 24h 0m | 256 MB | 2.5% |
| health-monitor | 🟢 Running | 24h 0m | 64 MB | 0.5% |

## API Connectivity

| Service | Status | Latency | Errors (1h) |
|---------|--------|---------|-------------|
| Gmail API | 🟢 Connected | 150ms | 0 |
| Odoo API | 🟢 Connected | 50ms | 0 |

## Resources

| Metric | Current | Warning | Critical |
|--------|---------|---------|----------|
| CPU | 15% | 70% | 90% |
| Memory | 45% | 80% | 95% |
| Disk | 32% | 85% | 95% |

## Recent Incidents

None in the last 24 hours.

## Uptime

- 30-day uptime: 99.7%
- Last downtime: 2026-01-25 03:00-03:05 (planned maintenance)

---
*Auto-generated by Health Monitor*
```

**Validation Rules**:
- `overall_status` calculated from component statuses
- `degraded` if any API errors or warnings exceeded
- `critical` if any process stopped or thresholds exceeded
- Incidents logged with timestamp and resolution

---

### 5. UpdateFile

**Purpose**: Cloud-written updates for local Dashboard merging.

**Storage**: `AI_Employee_Vault/Updates/{type}_{date}.md`

```yaml
---
type: update
update_type: email_summary          # email_summary | task_summary | alert
date: 2026-01-28
generated_by: cloud
generated_at: 2026-01-28T10:30:00Z
merge_status: pending               # pending | merged | skipped
merge_target: Dashboard.md
---

# Email Summary: 2026-01-28

**Generated by**: Cloud Agent
**Period**: 2026-01-28 00:00 - 10:30

## Inbox Activity

| Metric | Count |
|--------|-------|
| New emails received | 12 |
| Urgent (drafted) | 3 |
| Normal (queued) | 7 |
| Low priority | 2 |

## Draft Responses Created

1. **Re: Invoice Request** - Acme Corp
   - Pending approval: /Pending_Approval/email/DRAFT_20260128_001.md

2. **Re: Project Status** - Beta Inc
   - Pending approval: /Pending_Approval/email/DRAFT_20260128_002.md

3. **Re: Meeting Confirmation** - Client X
   - Pending approval: /Pending_Approval/email/DRAFT_20260128_003.md

## Awaiting Local Processing

- 2 emails flagged as requiring WhatsApp follow-up
- 1 email requires payment processing

---
*Merge this into Dashboard.md when local comes online*
```

**Validation Rules**:
- `update_type` determines merge behavior
- `merge_status` updated by local agent
- Old updates cleaned after 7 days
- Only local agent writes to Dashboard.md

---

## Modified Entities (from Gold Tier)

### 6. LoopState (Enhanced)

**Purpose**: Ralph Wiggum loop state with distributed agent support.

**Storage**: `AI_Employee_Vault/Plans/LOOP-{id}_state.json`

**Changes**:
- Added `agent_id` field to identify executing agent
- Added `claimed_from` to track original task location
- Added `sync_required` flag for cross-agent handoff

```json
{
  "loop_id": "loop_20260128103000",
  "agent_id": "cloud",                    // NEW: which agent is running this
  "prompt": "Draft response to client email",
  "iterations": 3,
  "max_iterations": 10,
  "status": "completed",
  "output_history": [
    {
      "iteration": 1,
      "timestamp": "2026-01-28T10:30:05Z",
      "action": "Read email content",
      "result": "Parsed client inquiry about pricing"
    },
    {
      "iteration": 2,
      "timestamp": "2026-01-28T10:30:30Z",
      "action": "Draft response",
      "result": "Created draft in /Drafts"
    },
    {
      "iteration": 3,
      "timestamp": "2026-01-28T10:30:45Z",
      "action": "Create approval request",
      "result": "Moved to /Pending_Approval/email/"
    }
  ],
  "claimed_from": "/Needs_Action/email/EMAIL_20260128_001.md",  // NEW
  "sync_required": true,                   // NEW: Git push after completion
  "paused_at": null,
  "awaiting_approval": null,
  "created_at": "2026-01-28T10:30:00Z",
  "completed_at": "2026-01-28T10:30:50Z"
}
```

---

### 7. ApprovalRequest (Enhanced)

**Purpose**: Action requiring human approval with agent source tracking.

**Storage**: `AI_Employee_Vault/Pending_Approval/{domain}/{type}_{id}.md`

**Changes**:
- Added `source_agent` field
- Added `requires_local_action` flag

```yaml
---
type: approval_request
action_type: send_email
source_agent: cloud                       # NEW: which agent created this
requires_local_action: true               # NEW: must be executed locally
priority: normal
created_at: 2026-01-28T10:30:45Z
expires_at: 2026-01-28T22:30:45Z
status: pending
related_task: /In_Progress/cloud/EMAIL_20260128_001.md

# Action details
email_to: client@acmecorp.com
email_subject: "Re: Pricing Inquiry"
email_draft_path: /Drafts/email/DRAFT_20260128_001.md
---

# Approval Request: Send Email to Acme Corp

## Status: ⏳ Pending Approval

## Details

| Field | Value |
|-------|-------|
| Action | Send Email |
| To | client@acmecorp.com |
| Subject | Re: Pricing Inquiry |
| Created By | Cloud Agent |
| Requires | Local execution |

## Draft Preview

> Dear valued client,
>
> Thank you for your inquiry about our pricing...
> [See full draft]

## Approval Instructions

1. Review the draft at `/Drafts/email/DRAFT_20260128_001.md`
2. Move this file to `/Approved/email/` to send
3. Or move to `/Rejected/email/` to discard

---
*Created by Cloud Agent | Requires local approval and execution*
```

---

## Domain Subfolders

Platinum Tier introduces domain-specific subfolders for better task isolation:

```
AI_Employee_Vault/
├── Needs_Action/
│   ├── email/               # Email triage tasks
│   ├── accounting/          # Odoo-related tasks
│   ├── social/              # Social media tasks
│   └── local/               # Tasks requiring local-only processing
│
├── Plans/
│   ├── email/
│   ├── accounting/
│   └── general/
│
├── Pending_Approval/
│   ├── email/               # Draft emails awaiting send approval
│   ├── accounting/          # Draft invoices awaiting post approval
│   ├── social/              # Draft posts awaiting publish approval
│   └── payments/            # Payments awaiting approval
│
├── In_Progress/
│   ├── cloud/               # Tasks claimed by cloud agent
│   └── local/               # Tasks claimed by local agent
│
├── Approved/
│   ├── email/
│   ├── accounting/
│   ├── social/
│   └── payments/
│
├── Rejected/
│   └── ... (same structure)
│
├── Done/
│   └── ... (flat, timestamped)
│
├── Updates/                  # NEW: Cloud-written updates
│   └── {type}_{date}.md
│
├── Signals/                  # NEW: Optional inter-agent signals
│   └── {signal_type}.json
│
└── Health/                   # NEW: Health status
    ├── status.md
    └── sync_state.json
```

---

## Entity Relationships (Updated)

```
AgentIdentity
    │
    ├── owns → TaskClaim[]
    ├── writes → SyncState
    ├── generates → HealthStatus (cloud only)
    └── creates → UpdateFile[] (cloud only)

TaskClaim
    │
    ├── references → Original task file
    ├── owned_by → AgentIdentity
    └── produces → ApprovalRequest | DoneFile

SyncState
    │
    ├── tracks → Git operations
    └── logs → Sync history

HealthStatus
    │
    ├── monitors → Processes
    ├── monitors → API connectivity
    └── monitors → System resources

UpdateFile
    │
    ├── generated_by → Cloud AgentIdentity
    └── merged_by → Local AgentIdentity

LoopState (from Gold)
    │
    ├── executed_by → AgentIdentity (NEW)
    └── produces → ApprovalRequest | DoneFile

ApprovalRequest (from Gold)
    │
    ├── created_by → AgentIdentity (NEW)
    └── processed_by → Local AgentIdentity (always)
```

---

## Vault Folder Structure (Complete)

```
AI_Employee_Vault/
├── Inbox/                    # Raw incoming items
├── Needs_Action/             # Watcher outputs
│   ├── email/
│   ├── accounting/
│   ├── social/
│   └── local/                # Tasks requiring local processing
├── Plans/                    # Claude reasoning outputs
│   ├── email/
│   ├── accounting/
│   ├── general/
│   └── LOOP-*_state.json     # Loop state files
├── In_Progress/              # NEW: Claimed tasks
│   ├── cloud/                # Cloud agent's tasks
│   └── local/                # Local agent's tasks
├── Pending_Approval/         # Awaiting human decision
│   ├── email/
│   ├── accounting/
│   ├── social/
│   └── payments/
├── Approved/                 # Human-approved
│   └── ... (domain subfolders)
├── Rejected/                 # Human-rejected
│   └── ... (domain subfolders)
├── Done/                     # Completed items
├── Logs/                     # JSON audit logs
├── Accounting/               # Financial data (from Gold)
│   ├── Invoices/
│   ├── Payments/
│   └── Transactions/
├── Briefings/                # CEO briefings
├── Social/                   # Social media (from Gold)
│   ├── Drafts/
│   └── Metrics/
├── Drop/                     # File upload drop folder
├── Updates/                  # NEW: Cloud-written updates
├── Signals/                  # NEW: Inter-agent signals
├── Health/                   # NEW: Health monitoring
│   ├── status.md
│   └── sync_state.json
├── Dashboard.md              # Single-writer: LOCAL ONLY
├── Company_Handbook.md       # Operational rules
└── Business_Goals.md         # Objectives and metrics
```

---

**Data Model Status**: COMPLETE - Ready for API contract definition.
