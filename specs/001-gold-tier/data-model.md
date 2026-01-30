# Data Model: Gold Tier - Autonomous Employee

**Feature**: Gold Tier
**Date**: 2026-01-25
**Status**: Complete

## Overview

This document defines the data entities for Gold Tier features. All entities are stored as markdown files with YAML frontmatter in the Obsidian vault, consistent with the existing Silver Tier patterns.

---

## Core Entities

### 1. OdooConnection

**Purpose**: Configuration and state for Odoo instance connection.

**Storage**: `config/odoo_config.json` (excluded from vault sync)

```yaml
# Schema
OdooConnection:
  url: string              # Base URL (e.g., https://mycompany.odoo.com)
  database: string         # Database name
  username: string         # Odoo username
  api_key: string          # API key (never password)
  last_sync: datetime      # Last successful sync timestamp
  sync_interval: integer   # Seconds between syncs (default: 300)
  models_enabled:          # Which Odoo models to sync
    - account.move         # Invoices
    - account.payment      # Payments
    - res.partner          # Contacts (optional)

  # Runtime state (not persisted)
  uid: integer             # Authenticated user ID
  is_connected: boolean    # Connection status
  last_error: string       # Last error message if any
```

**Validation Rules**:
- `url` must be valid HTTPS URL
- `database` must not be empty
- `api_key` minimum 32 characters
- `sync_interval` minimum 60 seconds

---

### 2. Invoice

**Purpose**: Represents an Odoo invoice synced to vault.

**Storage**: `AI_Employee_Vault/Accounting/Invoices/INV-{number}_{date}.md`

```yaml
---
# YAML Frontmatter
type: invoice
source: odoo
odoo_id: 12345                    # Odoo record ID
number: "INV/2026/0001"           # Invoice number
partner_id: 789                   # Odoo partner ID
partner_name: "Acme Corp"         # Customer name
invoice_date: 2026-01-20          # Invoice date
due_date: 2026-02-20              # Payment due date
state: posted                     # draft | posted | cancel
payment_state: not_paid           # not_paid | partial | paid | reversed
currency: USD
amount_untaxed: 1000.00           # Subtotal
amount_tax: 100.00                # Tax amount
amount_total: 1100.00             # Grand total
amount_residual: 1100.00          # Amount still due
synced_at: 2026-01-25T14:30:00Z   # Last sync timestamp
---

# Invoice: INV/2026/0001

**Customer**: Acme Corp
**Date**: 2026-01-20
**Due**: 2026-02-20
**Status**: Posted (Not Paid)

## Line Items

| Description | Quantity | Unit Price | Amount |
|-------------|----------|------------|--------|
| Consulting Services | 10 hrs | $100.00 | $1,000.00 |

## Totals

- Subtotal: $1,000.00
- Tax (10%): $100.00
- **Total Due**: $1,100.00

## Notes

[Synced from Odoo on 2026-01-25]
```

**Validation Rules**:
- `odoo_id` must be positive integer
- `number` must match Odoo format
- `amount_total` = `amount_untaxed` + `amount_tax`
- `amount_residual` <= `amount_total`
- `state` must be one of: draft, posted, cancel

---

### 3. Payment

**Purpose**: Represents a payment record synced from Odoo.

**Storage**: `AI_Employee_Vault/Accounting/Payments/PAY-{ref}_{date}.md`

```yaml
---
# YAML Frontmatter
type: payment
source: odoo
odoo_id: 5678                     # Odoo record ID
name: "CUST.IN/2026/0001"         # Payment reference
partner_id: 789                   # Odoo partner ID
partner_name: "Acme Corp"         # Payer/Payee name
payment_type: inbound             # inbound | outbound
payment_date: 2026-01-25          # Payment date
journal_id: 1                     # Bank/Cash journal
journal_name: "Bank"              # Journal display name
currency: USD
amount: 500.00                    # Payment amount
state: posted                     # draft | posted | cancelled
reconciled_invoice_ids: [12345]   # Linked invoice Odoo IDs
synced_at: 2026-01-25T15:00:00Z   # Last sync timestamp
---

# Payment: CUST.IN/2026/0001

**From**: Acme Corp
**Date**: 2026-01-25
**Type**: Customer Payment (Inbound)
**Status**: Posted

## Details

- Amount: $500.00 USD
- Journal: Bank
- Applied to: INV/2026/0001

## Notes

[Synced from Odoo on 2026-01-25]
```

**Validation Rules**:
- `payment_type` must be inbound or outbound
- `amount` must be positive
- `state` must be one of: draft, posted, cancelled

---

### 4. Transaction

**Purpose**: Daily transaction log for accounting activity.

**Storage**: `AI_Employee_Vault/Accounting/Transactions/{date}.md`

```yaml
---
# YAML Frontmatter
type: transaction_log
date: 2026-01-25
total_inbound: 1500.00
total_outbound: 300.00
net_change: 1200.00
transaction_count: 5
synced_at: 2026-01-25T23:59:00Z
---

# Transaction Log: 2026-01-25

## Summary

| Metric | Amount |
|--------|--------|
| Total Inbound | $1,500.00 |
| Total Outbound | $300.00 |
| Net Change | +$1,200.00 |
| Transactions | 5 |

## Transactions

### Inbound

| Time | Reference | Partner | Amount |
|------|-----------|---------|--------|
| 09:15 | CUST.IN/2026/0001 | Acme Corp | $500.00 |
| 14:30 | CUST.IN/2026/0002 | Beta Inc | $1,000.00 |

### Outbound

| Time | Reference | Partner | Amount |
|------|-----------|---------|--------|
| 11:00 | SUPP.OUT/2026/0001 | Supplier Co | $300.00 |

---

[Auto-generated by Odoo sync]
```

---

### 5. SocialPost

**Purpose**: Social media post draft and published state.

**Storage**:
- Draft: `AI_Employee_Vault/Social/Drafts/{platform}_{timestamp}.md`
- Published: Moved to `AI_Employee_Vault/Done/` after publishing

```yaml
---
# YAML Frontmatter
type: social_post
platform: facebook                # facebook | instagram | twitter
status: draft                     # draft | pending_approval | approved | published | failed
created_at: 2026-01-25T10:00:00Z
scheduled_for: 2026-01-25T14:00:00Z  # Optional scheduled time
approval_id: null                 # Set when approval requested
post_id: null                     # Platform post ID after publishing
content_type: text                # text | image | carousel | video
media_urls: []                    # Attached media paths
hashtags: ["#business", "#update"]
mentions: []                      # @mentions
---

# Social Post Draft

**Platform**: Facebook
**Type**: Text Post
**Created**: 2026-01-25 10:00 AM

## Content

Weekly business update: We've completed 15 client projects this month and are
on track to exceed Q1 targets. Thank you to our amazing team!

#business #update

## Validation

- [x] Character count: 156/63206 (Facebook limit)
- [x] No prohibited content detected
- [x] Hashtag count: 2 (recommended: 3-5)

## Approval

Status: Draft - Awaiting submission for approval

---

[Created by social_posting skill]
```

**Validation Rules**:
- `platform` must be: facebook, instagram, twitter
- `status` transitions: draft → pending_approval → approved → published
- Character limits: Facebook 63206, Instagram 2200, Twitter 280
- Instagram requires at least one media attachment

---

### 6. Engagement

**Purpose**: Social media metrics for a published post.

**Storage**: `AI_Employee_Vault/Social/Metrics/{platform}_{post_id}.md`

```yaml
---
# YAML Frontmatter
type: engagement
platform: facebook
post_id: "fb_123456789"
source_draft: "facebook_20260125100000.md"
published_at: 2026-01-25T14:05:00Z
last_updated: 2026-01-25T20:00:00Z
metrics:
  impressions: 1500
  reach: 1200
  likes: 45
  comments: 8
  shares: 12
  saves: 3                        # Instagram only
  retweets: 0                     # Twitter only
  quote_tweets: 0                 # Twitter only
  engagement_rate: 4.3            # (interactions/reach) * 100
---

# Engagement Report: Facebook Post

**Post ID**: fb_123456789
**Published**: 2026-01-25 2:05 PM
**Last Updated**: 2026-01-25 8:00 PM

## Metrics

| Metric | Value |
|--------|-------|
| Impressions | 1,500 |
| Reach | 1,200 |
| Likes | 45 |
| Comments | 8 |
| Shares | 12 |
| **Engagement Rate** | 4.3% |

## Trend (24h)

- Likes: +45 (new post)
- Comments: +8
- Shares: +12

## Top Comments

> "Great update! Looking forward to more." - User1
> "Congrats on the milestone!" - User2

---

[Fetched from Facebook Graph API]
```

---

### 7. CEOBriefing

**Purpose**: Weekly CEO briefing report.

**Storage**: `AI_Employee_Vault/Briefings/{date}_Monday_Briefing.md`

```yaml
---
# YAML Frontmatter
type: ceo_briefing
period_start: 2026-01-19
period_end: 2026-01-25
generated_at: 2026-01-25T23:00:00Z
generator: ceo_briefing_skill
version: 1.0
sections:
  - revenue_summary
  - expense_summary
  - task_completion
  - bottlenecks
  - suggestions
metrics:
  total_revenue: 15000.00
  total_expenses: 3500.00
  net_income: 11500.00
  tasks_completed: 47
  tasks_pending: 12
  bottleneck_count: 3
  suggestion_count: 2
---

# CEO Briefing: Week of January 19-25, 2026

**Generated**: Sunday, January 25, 2026 at 11:00 PM
**Period**: January 19 - January 25, 2026

---

## Executive Summary

This week showed strong financial performance with $15,000 in revenue against
$3,500 in expenses, yielding a net income of $11,500. Task completion rate
was 80% (47/59 tasks), with 3 bottlenecks requiring attention.

---

## Revenue Summary

| Source | Amount | vs. Last Week |
|--------|--------|---------------|
| Consulting | $10,000 | +15% |
| Product Sales | $3,500 | -5% |
| Subscriptions | $1,500 | +0% |
| **Total** | **$15,000** | **+8%** |

### Outstanding Invoices

- INV/2026/0015 - Acme Corp - $2,500 (Due: Jan 30)
- INV/2026/0018 - Beta Inc - $1,800 (Due: Feb 5)

---

## Expense Summary

| Category | Amount | vs. Budget |
|----------|--------|------------|
| Operations | $2,000 | On budget |
| Subscriptions | $800 | On budget |
| Marketing | $500 | Under budget |
| Misc | $200 | On budget |
| **Total** | **$3,500** | **On budget** |

---

## Task Completion

**Completed This Week**: 47 tasks
**Still Pending**: 12 tasks
**Completion Rate**: 80%

### Highlights

- Launched new client portal (Project Alpha)
- Completed Q1 financial audit
- Automated invoice reminders

---

## Bottlenecks

### 1. Supplier Response Delay
- **Age**: 5 days in Needs_Action
- **Impact**: Blocking inventory reorder
- **Recommendation**: Escalate to alternative supplier

### 2. Client Contract Review
- **Age**: 4 days in Pending_Approval
- **Impact**: Delaying project start
- **Recommendation**: Schedule review meeting

### 3. Payment Gateway Issue
- **Age**: 3 days (recurring)
- **Impact**: 2 failed transactions
- **Recommendation**: Contact gateway support

---

## Proactive Suggestions

### 1. Consolidate SaaS Subscriptions
**Potential Savings**: $150/month

Analysis shows 3 overlapping tools for project management. Consolidating
to a single tool would reduce costs and improve workflow.

**Action**: Review Asana, Monday, and ClickUp usage; pick one.

### 2. Early Invoice Payment Discount
**Potential Savings**: $200/month

Offering 2% early payment discount to top 5 clients could accelerate
cash flow and reduce outstanding receivables.

**Action**: Draft discount policy for approval.

---

## Goals Progress (from Business_Goals.md)

| Goal | Target | Actual | Status |
|------|--------|--------|--------|
| Q1 Revenue | $50,000 | $35,000 | On Track (70%) |
| Client Retention | 95% | 98% | Exceeding |
| Response Time | <4h | 3.2h | Meeting |
| Task Completion | 85% | 80% | Needs Attention |

---

## Next Week Focus

1. Clear bottlenecks (3 items)
2. Follow up on outstanding invoices ($4,300)
3. Implement SaaS consolidation suggestion
4. Prepare Q1 interim report

---

*This briefing was automatically generated by the AI Employee.*
*Review and verify all figures before taking action.*
```

**Validation Rules**:
- `period_end` must be Saturday or Sunday
- All monetary values must be non-negative
- `tasks_completed` + pending should sum correctly
- At least 2 suggestions required
- All sections must be populated

---

### 8. LoopState (Enhanced)

**Purpose**: Ralph Wiggum loop state with pause/resume support.

**Storage**: `AI_Employee_Vault/Plans/LOOP-{id}_state.json`

```json
{
  "loop_id": "loop_20260125143000",
  "prompt": "Process all files in Needs_Action and generate CEO briefing",
  "iterations": 5,
  "max_iterations": 10,
  "status": "paused",
  "output_history": [
    {
      "iteration": 1,
      "timestamp": "2026-01-25T14:30:05Z",
      "action": "Read Needs_Action folder",
      "result": "Found 12 files"
    },
    {
      "iteration": 2,
      "timestamp": "2026-01-25T14:30:30Z",
      "action": "Process EMAIL_20260125_001.md",
      "result": "Classified as client inquiry"
    }
  ],
  "paused_at": "2026-01-25T14:35:00Z",
  "awaiting_approval": "APR-20260125-003",
  "approval_reason": "Payment action requires human approval",
  "context": {
    "current_file": "PAYMENT_20260125_002.md",
    "pending_actions": ["send_payment", "log_transaction"]
  },
  "created_at": "2026-01-25T14:30:00Z",
  "last_activity": "2026-01-25T14:35:00Z"
}
```

**State Transitions**:
- `running` → `paused` (awaiting approval)
- `paused` → `running` (approval granted)
- `paused` → `failed` (approval rejected)
- `running` → `completed` (TASK_COMPLETE or file moved)
- `running` → `failed` (max iterations or timeout)

---

## Entity Relationships

```
OdooConnection
    │
    ├── syncs → Invoice[]
    ├── syncs → Payment[]
    └── generates → Transaction (daily log)

SocialPost
    │
    └── generates → Engagement (after publishing)

CEOBriefing
    │
    ├── aggregates ← Invoice[]
    ├── aggregates ← Payment[]
    ├── aggregates ← Done/* (completed tasks)
    ├── reads ← Business_Goals.md
    └── analyzes ← Needs_Action/* (bottlenecks)

LoopState
    │
    ├── references → Approval request
    └── produces → Plan files, Action files
```

---

## Vault Folder Structure (Updated)

```
AI_Employee_Vault/
├── Inbox/                    # Raw incoming items
├── Needs_Action/             # Watcher outputs
├── Plans/                    # Claude reasoning outputs
│   └── LOOP-*_state.json     # Ralph Wiggum state files
├── Pending_Approval/         # Awaiting human decision
├── Approved/                 # Human-approved
├── Rejected/                 # Human-rejected
├── Done/                     # Completed items
├── Logs/                     # JSON audit logs
├── Accounting/               # NEW: Financial data
│   ├── Invoices/             # INV-*.md files
│   ├── Payments/             # PAY-*.md files
│   └── Transactions/         # Daily transaction logs
├── Briefings/                # CEO briefing outputs
│   └── YYYY-MM-DD_Monday_Briefing.md
├── Social/                   # NEW: Social media data
│   ├── Drafts/               # Post drafts
│   └── Metrics/              # Engagement metrics
├── Drop/                     # File upload drop folder
├── Dashboard.md              # Real-time status
├── Company_Handbook.md       # Operational rules
└── Business_Goals.md         # Objectives and metrics
```

---

**Data Model Status**: COMPLETE - Ready for API contract definition.
