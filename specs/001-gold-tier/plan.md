# Implementation Plan: Gold Tier - Autonomous Employee

**Branch**: `001-gold-tier` | **Date**: 2026-01-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-gold-tier/spec.md`

## Summary

The Gold Tier transforms the AI Employee from a functional assistant into a fully autonomous employee by adding:
1. **Odoo Accounting Integration** - Financial visibility via JSON-RPC API
2. **Weekly CEO Briefing Generation** - Proactive business intelligence
3. **Social Media Integration** - Facebook, Instagram, Twitter/X posting with approval workflows
4. **Ralph Wiggum Loop Enhancement** - Already built, needs pause/resume for mid-loop approvals
5. **Multiple MCP Servers** - Isolated action execution per domain

The approach builds on the existing Silver Tier infrastructure (watchers, HITL, orchestrator, email MCP) by adding new MCP servers and skills following established patterns.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastAPI (MCP servers), httpx (JSON-RPC), playwright (browser automation fallback), pydantic (data validation)
**Storage**: Obsidian Vault (markdown files), JSON logs
**Testing**: pytest with fixtures from existing conftest.py
**Target Platform**: Windows/Linux (local-first), Python runtime
**Project Type**: Single project with modular components
**Performance Goals**: Process 50+ accounting transactions/day, publish social posts within 5 minutes of approval
**Constraints**: Local-first (no cloud sync), all sensitive actions require HITL approval, rate limits enforced
**Scale/Scope**: Single business owner, 1 Odoo instance, 3 social media platforms

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Status | Implementation Notes |
|-----------|--------|---------------------|
| I. Local-First Privacy | PASS | All data stored in vault, external API calls logged |
| II. Human-in-the-Loop | PASS | All social posts, invoice sends require approval; payments >$100 require approval |
| III. Audit Everything | PASS | All MCP actions logged with ISO 8601 timestamps, action type, actor, result |
| IV. Graceful Degradation | PASS | Circuit breakers per MCP server, queue actions when services unavailable |
| V. Separation of Concerns | PASS | Watchers detect → Skills reason → MCP servers execute |
| VI. Agent Skills Architecture | PASS | CEO Briefing, Social Media as skills in .claude/commands/ |
| VII. Defensive Defaults | PASS | DRY_RUN=true, rate limits (10 emails/hr, 3 payments/hr, 5 social posts/day) |

**Gate Status**: PASS - Proceeding to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/001-gold-tier/
├── plan.md              # This file
├── research.md          # Phase 0 output - technology decisions
├── data-model.md        # Phase 1 output - entity definitions
├── quickstart.md        # Phase 1 output - getting started guide
├── contracts/           # Phase 1 output - API contracts
│   ├── odoo-mcp.yaml    # Odoo MCP server OpenAPI spec
│   ├── social-mcp.yaml  # Social Media MCP server OpenAPI spec
│   └── briefing-skill.yaml  # CEO Briefing skill contract
└── tasks.md             # Phase 2 output (created by /sp.tasks)
```

### Source Code (repository root)

```text
src/
├── watchers/
│   ├── base_watcher.py          # Existing - base class
│   ├── filesystem_watcher.py    # Existing - file drops
│   ├── gmail_watcher.py         # Existing - email monitoring
│   ├── whatsapp_watcher.py      # Existing - WhatsApp messages
│   ├── linkedin_watcher.py      # Existing - LinkedIn notifications
│   └── odoo_watcher.py          # NEW - Odoo invoice/payment events
├── mcp_servers/
│   ├── email_mcp.py             # Existing - email actions
│   ├── odoo_mcp.py              # NEW - Odoo accounting actions
│   └── social_mcp.py            # NEW - Facebook/Instagram/Twitter actions
├── skills/
│   ├── process_inbox.py         # Existing - inbox processing
│   ├── linkedin_posting.py      # Existing - LinkedIn posts
│   ├── ceo_briefing.py          # NEW - weekly briefing generation
│   └── social_posting.py        # NEW - multi-platform social posting
├── utils/
│   ├── hitl.py                  # Existing - approval workflow
│   ├── ralph_wiggum.py          # Existing - reasoning loop (enhance for pause/resume)
│   └── retry_handler.py         # Existing - circuit breakers, rate limiting
└── lib/
    └── odoo_client.py           # NEW - Odoo JSON-RPC client library

tests/
├── contract/
│   ├── test_odoo_mcp_contract.py    # NEW
│   └── test_social_mcp_contract.py  # NEW
├── integration/
│   ├── test_odoo_integration.py     # NEW
│   ├── test_social_integration.py   # NEW
│   └── test_ceo_briefing.py         # NEW
└── unit/
    ├── test_base_watcher.py         # Existing
    ├── test_filesystem_watcher.py   # Existing
    ├── test_linkedin_watcher.py     # Existing
    ├── test_linkedin_posting.py     # Existing
    ├── test_process_inbox.py        # Existing
    ├── test_ralph_wiggum.py         # Existing
    ├── test_odoo_client.py          # NEW
    └── test_odoo_watcher.py         # NEW

.claude/commands/
├── ceo-briefing.md                  # NEW - CEO briefing skill definition
└── social-posting.md                # NEW - Social media posting skill

AI_Employee_Vault/
├── Accounting/                      # Odoo sync destination
│   ├── Invoices/                    # Invoice records
│   ├── Payments/                    # Payment records
│   └── Transactions/                # Transaction log
├── Briefings/                       # CEO briefing output
└── Social/                          # Social media drafts and metrics
    ├── Drafts/
    └── Metrics/
```

**Structure Decision**: Single project structure maintained. New components follow existing patterns (watchers inherit from BaseWatcher, MCP servers follow EmailMCP patterns, skills follow ProcessInboxSkill patterns).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 3 MCP Servers (email, odoo, social) | Platform-specific APIs require isolation | Combined server would violate separation of concerns, make circuit breakers less effective |
| Browser automation fallback | Some platforms lack reliable APIs | API-only approach rejected because Instagram official API has severe limitations |

## Phase 0: Research Summary

See [research.md](./research.md) for detailed findings.

### Key Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Odoo Connection | JSON-RPC via xmlrpc.client (built-in) | No external dependency, Odoo's native protocol, well-documented |
| Facebook/Instagram | Meta Graph API + Playwright fallback | Official API for Pages, browser automation for personal profiles |
| Twitter/X | API v2 (OAuth 2.0) + Playwright fallback | API preferred, browser fallback for rate limit mitigation |
| CEO Briefing Schedule | Python schedule library (existing dependency) | Simple, already used by orchestrator |
| Accounting Data Model | Vault markdown files with YAML frontmatter | Consistent with existing patterns, human-readable, git-friendly |

## Phase 1: Design Artifacts

### Data Model

See [data-model.md](./data-model.md) for complete entity definitions.

**Core Entities**:
- **OdooConnection**: Connection configuration and session state
- **Invoice**: Odoo invoice with line items, status, due dates
- **Payment**: Payment record with reconciliation status
- **Transaction**: General accounting entry
- **SocialPost**: Platform-agnostic post with media and scheduling
- **Engagement**: Social media metrics (likes, comments, shares)
- **CEOBriefing**: Weekly report with sections for revenue, tasks, suggestions

### API Contracts

See [contracts/](./contracts/) directory for OpenAPI specifications.

**Odoo MCP Server** (`contracts/odoo-mcp.yaml`):
- `sync_invoices()` - Fetch new/updated invoices from Odoo
- `sync_payments()` - Fetch payment records
- `create_draft_invoice()` - Create invoice in draft status
- `get_account_balance()` - Current account balances
- `health_check()` - Server health status

**Social Media MCP Server** (`contracts/social-mcp.yaml`):
- `draft_post()` - Create post draft for approval
- `publish_post()` - Publish approved post to platform
- `get_engagement()` - Retrieve post metrics
- `validate_content()` - Platform-specific validation
- `health_check()` - Server health status

**CEO Briefing Skill** (`contracts/briefing-skill.yaml`):
- `generate_briefing()` - Create weekly CEO briefing
- `get_revenue_summary()` - Revenue metrics for period
- `get_task_summary()` - Completed tasks and bottlenecks
- `get_suggestions()` - Proactive optimization suggestions

### Quickstart Guide

See [quickstart.md](./quickstart.md) for setup instructions.

## Implementation Phases

### Phase 1: Odoo Integration (P1)

1. **Odoo Client Library** (`src/lib/odoo_client.py`)
   - JSON-RPC connection with authentication
   - Model access: account.move, account.payment, account.account
   - Error handling with retry logic

2. **Odoo Watcher** (`src/watchers/odoo_watcher.py`)
   - Poll Odoo for new invoices/payments
   - Create action files in Needs_Action
   - Handle connection failures gracefully

3. **Odoo MCP Server** (`src/mcp_servers/odoo_mcp.py`)
   - Sync operations to vault
   - Create draft invoices (approval required for send)
   - Circuit breaker integration

4. **Vault Accounting Structure**
   - Invoice files: `Accounting/Invoices/INV-{number}_{date}.md`
   - Payment files: `Accounting/Payments/PAY-{ref}_{date}.md`
   - Daily transaction log: `Accounting/Transactions/{date}.md`

### Phase 2: CEO Briefing (P1)

1. **CEO Briefing Skill** (`src/skills/ceo_briefing.py`)
   - Read Business_Goals.md for targets
   - Aggregate Accounting folder data
   - Scan Done folder for completed tasks
   - Identify bottlenecks (overdue tasks)
   - Generate optimization suggestions

2. **Scheduled Trigger**
   - Add to orchestrator schedule: Sunday 11 PM
   - Output: `Briefings/YYYY-MM-DD_Monday_Briefing.md`

3. **Claude Command** (`.claude/commands/ceo-briefing.md`)
   - Skill definition for manual triggering
   - Integration with process-inbox for action files

### Phase 3: Social Media Integration (P2)

1. **Social Media MCP Server** (`src/mcp_servers/social_mcp.py`)
   - Platform abstraction layer
   - Facebook Graph API integration
   - Instagram Graph API integration
   - Twitter/X API v2 integration
   - Playwright fallback handlers

2. **Social Posting Skill** (`src/skills/social_posting.py`)
   - Content validation per platform
   - Draft creation with preview
   - Approval workflow integration
   - Engagement metric retrieval

3. **Vault Social Structure**
   - Drafts: `Social/Drafts/PLATFORM_{timestamp}.md`
   - Metrics: `Social/Metrics/PLATFORM_{post_id}.md`

### Phase 4: Ralph Wiggum Enhancement (P2)

1. **Pause/Resume Support** (`src/utils/ralph_wiggum.py`)
   - Serialize loop state on approval pause
   - Resume from saved state after approval
   - Approval callback integration

2. **Mid-Loop Approval Flow**
   - Detect approval-required action in loop
   - Create approval request
   - Pause loop with state saved
   - Resume on approval (or abort on rejection)

### Phase 5: MCP Server Infrastructure (P3)

1. **Multi-Server Orchestration**
   - Update orchestrator for multiple MCP servers
   - Independent health checks per server
   - Circuit breaker isolation

2. **Audit Logging Enhancement**
   - Structured JSON logs for all MCP actions
   - Daily rotation: `Logs/YYYY-MM-DD.json`
   - 90-day retention policy implementation

## Dependencies & Prerequisites

### Silver Tier (Complete)

- [x] BaseWatcher class
- [x] Email MCP server
- [x] HITL approval workflow
- [x] Ralph Wiggum loop
- [x] Retry handler with circuit breakers
- [x] Orchestrator
- [x] Vault folder structure

### External Requirements

- [ ] Odoo Community Edition v19+ accessible
- [ ] Odoo API credentials (database, username, API key)
- [ ] Facebook Page + access token
- [ ] Instagram Business Account + access token
- [ ] Twitter/X Developer Account + OAuth 2.0 credentials
- [ ] Playwright installed for browser automation

## Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Odoo API changes | Low | High | Version-pin client, document API contract |
| Social media rate limits | Medium | Medium | Rate limiter, multiple accounts, browser fallback |
| Meta API deprecation | Low | High | Playwright fallback ready, monitor changelog |
| Long CEO briefing generation | Medium | Low | Timeout handling, partial report generation |

## Success Criteria Mapping

| Success Criteria | Implementation | Verification |
|-----------------|----------------|--------------|
| SC-001: View financial summary without Odoo login | CEO Briefing reads vault Accounting data | Integration test |
| SC-002: Briefing generated within 10 min, 99% reliability | Schedule + timeout handling | Monitoring |
| SC-003: Posts published within 5 min of approval | MCP server + approval watcher | Integration test |
| SC-004: 95% multi-step tasks complete autonomously | Ralph Wiggum pause/resume | Load test |
| SC-005: Recovery within 3 retries | Existing retry handler | Unit test |
| SC-006: Actions traceable within 24 hours | JSON audit logs | Audit test |
| SC-007: Handle 50+ transactions/day | Batch processing in Odoo sync | Performance test |
| SC-008: Engagement metrics within 1 hour | Scheduled metric retrieval | Integration test |

## Next Steps

1. Run `/sp.tasks` to generate actionable task list
2. Create feature branch `001-gold-tier`
3. Implement Phase 1 (Odoo Integration) first as it enables CEO Briefing
4. Implement Phase 2 (CEO Briefing) to deliver P1 value quickly
5. Implement Phase 3-5 in parallel where possible

---

**Plan Status**: COMPLETE - Ready for `/sp.tasks` to generate implementation tasks.
