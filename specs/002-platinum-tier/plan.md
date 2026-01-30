# Implementation Plan: Platinum Tier - Always-On Cloud + Local Executive

**Branch**: `002-platinum-tier` | **Date**: 2026-01-28 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-platinum-tier/spec.md`

## Summary

The Platinum Tier transforms the AI Employee from a local-only system into a hybrid Cloud/Local architecture providing 24/7 availability. Key features include:

1. **Cloud VM Deployment** - Always-on cloud agent for continuous monitoring (Oracle Cloud Free Tier)
2. **Work-Zone Specialization** - Clear boundaries between cloud (draft-only) and local (execution) capabilities
3. **Git-Based Vault Synchronization** - Real-time sync with claim-by-move task ownership
4. **Cloud Odoo Deployment** - Self-hosted Odoo for accounting with HTTPS
5. **Health Monitoring with Auto-Recovery** - PM2 process management with watchdog
6. **Security Architecture** - Secrets never sync to cloud; local-only sensitive operations

The approach extends the Gold Tier infrastructure with a split-brain architecture where the cloud agent handles perception and draft creation, while the local agent maintains exclusive control over approvals and sensitive action execution.

## Technical Context

**Language/Version**: Python 3.11+ (both agents)
**Primary Dependencies**: PM2 (process management), Git (sync), nginx (reverse proxy), PostgreSQL (Odoo)
**Storage**: Obsidian Vault (Git repo), Odoo PostgreSQL, local .env files
**Testing**: pytest for Python, integration tests for sync behavior
**Target Platform**: Cloud VM (Oracle Cloud ARM64/AMD64), Local (Windows/Linux/macOS)
**Project Type**: Distributed dual-agent system with shared vault
**Performance Goals**: 99.5% cloud uptime, <30s sync latency, <5min draft response time
**Constraints**: Zero secrets on cloud, WhatsApp local-only, payments local-only, HTTPS everywhere
**Scale/Scope**: Single business owner, 1 Odoo instance, 2 agents (cloud + local)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Pre-Design Status | Implementation Notes |
|-----------|-------------------|---------------------|
| I. Local-First Privacy | PASS | Cloud writes to vault only; .env/.tokens in .gitignore; WhatsApp/banking local-only |
| II. Human-in-the-Loop | PASS | All approvals processed by local agent only; cloud creates drafts |
| III. Audit Everything | PASS | Cloud logs to /Logs, syncs via Git; local merges; JSON audit trail preserved |
| IV. Graceful Degradation | PASS | Cloud operates independently when local offline; local operates when cloud offline |
| V. Separation of Concerns | PASS | Cloud: perception + draft; Local: approval + execution; Vault: shared state |
| VI. Agent Skills Architecture | PASS | Existing skills work on both agents; cloud-specific skills for draft-only operations |
| VII. Defensive Defaults | PASS | Cloud agent hardcoded to draft-only; DRY_RUN enforced until human override |

**Gate Status**: PASS - Proceeding to Phase 0 research.

### Post-Design Re-Check

| Principle | Post-Design Status | Verification Method |
|-----------|-------------------|---------------------|
| I. Local-First Privacy | PASS | .gitignore audit; sync test excludes secrets |
| II. Human-in-the-Loop | PASS | Cloud MCP blocks execution; approval workflow test |
| III. Audit Everything | PASS | Git commit logs + /Logs folder; audit trail test |
| IV. Graceful Degradation | PASS | Offline mode tests for both agents |
| V. Separation of Concerns | PASS | Work-zone enforcement tests |
| VI. Agent Skills Architecture | PASS | Skill compatibility tests |
| VII. Defensive Defaults | PASS | Cloud cannot execute; config audit |

## Project Structure

### Documentation (this feature)

```text
specs/002-platinum-tier/
├── plan.md              # This file
├── research.md          # Phase 0 output - technology decisions
├── data-model.md        # Phase 1 output - entity definitions
├── quickstart.md        # Phase 1 output - getting started guide
├── contracts/           # Phase 1 output - API contracts
│   ├── cloud-orchestrator.yaml  # Cloud agent API
│   ├── sync-protocol.yaml       # Git sync protocol
│   └── health-monitor.yaml      # Health check API
└── tasks.md             # Phase 2 output (created by /sp.tasks)
```

### Source Code (repository root)

```text
src/
├── watchers/
│   ├── base_watcher.py          # Existing - base class
│   ├── filesystem_watcher.py    # Existing - file drops
│   ├── gmail_watcher.py         # Existing - email monitoring (cloud-capable)
│   ├── whatsapp_watcher.py      # Existing - WhatsApp (LOCAL-ONLY)
│   ├── linkedin_watcher.py      # Existing - LinkedIn notifications
│   └── odoo_watcher.py          # Existing - Odoo monitoring (cloud-capable)
│
├── mcp_servers/
│   ├── email_mcp.py             # Existing - email actions (LOCAL-ONLY for send)
│   ├── odoo_mcp.py              # Existing - Odoo actions (cloud: draft-only)
│   └── social_mcp.py            # Existing - Social actions (LOCAL-ONLY for post)
│
├── cloud/                       # NEW: Cloud-specific components
│   ├── __init__.py
│   ├── cloud_orchestrator.py    # Cloud agent main entry point
│   ├── work_zone.py             # Work-zone enforcement logic
│   ├── sync_manager.py          # Git-based vault synchronization
│   └── health_monitor.py        # Process health monitoring
│
├── local/                       # NEW: Local-specific components
│   ├── __init__.py
│   ├── local_orchestrator.py    # Local agent (extends orchestrator.py)
│   ├── sync_puller.py           # Git pull on startup + periodic
│   └── dashboard_merger.py      # Merge /Updates into Dashboard.md
│
├── skills/
│   ├── process_inbox.py         # Existing - inbox processing
│   ├── ceo_briefing.py          # Existing - briefing generation
│   └── email_triage.py          # NEW - Cloud email triage skill
│
├── utils/
│   ├── hitl.py                  # Existing - approval workflow
│   ├── ralph_wiggum.py          # Existing - reasoning loop
│   ├── retry_handler.py         # Existing - circuit breakers
│   └── claim_lock.py            # NEW - claim-by-move implementation
│
└── lib/
    ├── odoo_client.py           # Existing - Odoo JSON-RPC
    └── social_clients/          # Existing - social media clients

tests/
├── contract/
│   ├── test_sync_protocol.py        # NEW - Sync behavior tests
│   └── test_work_zone.py            # NEW - Work-zone enforcement tests
├── integration/
│   ├── test_cloud_local_handoff.py  # NEW - End-to-end handoff test
│   ├── test_conflict_resolution.py  # NEW - Git conflict handling
│   └── test_claim_by_move.py        # NEW - Task ownership tests
└── unit/
    ├── test_cloud_orchestrator.py   # NEW
    ├── test_sync_manager.py         # NEW
    └── test_health_monitor.py       # NEW

deploy/                          # NEW: Deployment configurations
├── cloud/
│   ├── ecosystem.config.js      # PM2 configuration
│   ├── nginx.conf               # Nginx reverse proxy
│   ├── setup-cloud-vm.sh        # Cloud VM setup script
│   ├── odoo.conf                # Odoo server configuration
│   └── backup-cron.sh           # Automated backup script
└── local/
    └── setup-local-sync.sh      # Local Git sync setup

AI_Employee_Vault/               # Existing + New folders
├── Needs_Action/
│   ├── email/                   # NEW - Domain-specific subfolders
│   ├── accounting/
│   └── local/                   # NEW - Tasks requiring local processing
├── Plans/
│   └── domain/                  # NEW - Domain-specific plans
├── Pending_Approval/
│   ├── email/
│   ├── accounting/
│   ├── social/
│   └── payments/
├── In_Progress/                 # NEW - Claim-by-move ownership
│   ├── cloud/                   # Tasks claimed by cloud agent
│   └── local/                   # Tasks claimed by local agent
├── Updates/                     # NEW - Cloud-written updates
│   └── email_summary.md         # Daily email summary
├── Signals/                     # NEW - Inter-agent signals (optional)
├── Health/                      # NEW - Health status files
│   └── status.md
└── ... (existing folders)
```

**Structure Decision**: Distributed dual-agent system with separate cloud/ and local/ source directories. Shared vault via Git. Cloud agent runs subset of watchers (Gmail, filesystem, Odoo monitor) and MCP servers in draft-only mode. Local agent maintains full capabilities including WhatsApp, approvals, and action execution.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 2 Orchestrators (cloud + local) | Separate runtimes required for 24/7 availability | Single orchestrator cannot run when laptop closed |
| Git-based sync | Need offline operation for both agents | Real-time sync (WebSocket) requires both agents online |
| PM2 + Watchdog | Cloud process reliability for 99.5% uptime | Manual restart unacceptable for autonomous operation |
| Domain subfolders | Task isolation for claim-by-move | Flat folders cause race conditions |

## Phase 0: Research Summary

See [research.md](./research.md) for detailed findings.

### Key Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Cloud Provider | Oracle Cloud Free Tier (ARM64 Ampere) | Free, 24GB RAM, sufficient for Odoo + watchers |
| Process Manager | PM2 | Industry standard, auto-restart, log management |
| Vault Sync | Git push/pull with GitHub | Reliable, versioned, conflict detection built-in |
| Task Ownership | Claim-by-move to /In_Progress/<agent>/ | Atomic operation, no coordination needed |
| Odoo Deployment | Docker Compose (Odoo + PostgreSQL + nginx) | Isolated, reproducible, easy backup |
| Secret Management | .env local-only; cloud uses limited env vars | Zero secrets in Git; principle of least privilege |

## Phase 1: Design Artifacts

### Data Model

See [data-model.md](./data-model.md) for complete entity definitions.

**New Entities**:
- **AgentIdentity**: Cloud vs Local agent identification
- **TaskClaim**: Claim-by-move record for task ownership
- **SyncState**: Git sync status and last commit
- **HealthStatus**: Process health and uptime metrics
- **UpdateFile**: Cloud-written updates for Dashboard merging

**Modified Entities (from Gold)**:
- **LoopState**: Add `agent_id` field for distributed execution
- **ApprovalRequest**: Add `source_agent` field

### API Contracts

See [contracts/](./contracts/) directory for specifications.

**Cloud Orchestrator** (`contracts/cloud-orchestrator.yaml`):
- `get_status()` - Agent health and queue status
- `process_inbox_cloud()` - Cloud-side inbox processing (draft-only)
- `sync_vault()` - Trigger Git push
- `health_check()` - Process health endpoint

**Sync Protocol** (`contracts/sync-protocol.yaml`):
- `claim_task(task_id, agent_id)` - Claim task by moving to /In_Progress
- `release_task(task_id)` - Release unclaimed task
- `push_changes()` - Git add, commit, push
- `pull_changes()` - Git pull with conflict detection

**Health Monitor** (`contracts/health-monitor.yaml`):
- `check_process(name)` - Check if process is running
- `restart_process(name)` - Restart failed process via PM2
- `get_metrics()` - CPU, memory, disk usage
- `send_alert(message)` - Notification on critical failure

### Quickstart Guide

See [quickstart.md](./quickstart.md) for setup instructions.

## Implementation Phases

### Phase 1: Cloud Infrastructure Setup (P0)

1. **Cloud VM Provisioning** (`deploy/cloud/setup-cloud-vm.sh`)
   - Oracle Cloud ARM64 VM creation
   - Security group configuration (SSH, HTTP, HTTPS)
   - Python 3.11+, Node.js 24+, Git installation
   - PM2 global installation

2. **Nginx Reverse Proxy** (`deploy/cloud/nginx.conf`)
   - HTTPS termination with Let's Encrypt
   - Proxy to Odoo (port 8069)
   - Health check endpoint

3. **Odoo Cloud Deployment** (`deploy/cloud/odoo.conf`)
   - Docker Compose for Odoo + PostgreSQL
   - HTTPS via nginx
   - Automated backup script

### Phase 2: Vault Synchronization (P0)

1. **Git Sync Manager** (`src/cloud/sync_manager.py`)
   - Git operations wrapper (add, commit, push, pull)
   - Conflict detection and resolution strategy
   - Sync interval configuration (default: 30s)
   - Error handling with retry

2. **Claim-by-Move Implementation** (`src/utils/claim_lock.py`)
   - Atomic move operation using Git
   - Agent identity stamping
   - Collision detection (first mover wins)
   - Claim release on timeout

3. **Local Sync Puller** (`src/local/sync_puller.py`)
   - Git pull on startup
   - Periodic pull (every 60s)
   - Merge /Updates into Dashboard.md
   - Conflict notification

### Phase 3: Work-Zone Specialization (P1)

1. **Work-Zone Enforcer** (`src/cloud/work_zone.py`)
   - Define cloud-allowed actions (read, draft, create approval)
   - Define local-only actions (send, post, pay, approve)
   - Decorator for MCP methods
   - Audit logging for blocked attempts

2. **Cloud Orchestrator** (`src/cloud/cloud_orchestrator.py`)
   - Extends base Orchestrator
   - Loads only cloud-compatible watchers
   - Enforces draft-only MCP mode
   - Git sync after each task

3. **Local Orchestrator Enhancement** (`src/local/local_orchestrator.py`)
   - Git pull on startup
   - Dashboard merger integration
   - Process Approved/ folder
   - Full MCP execution capability

### Phase 4: Health Monitoring (P1)

1. **Health Monitor** (`src/cloud/health_monitor.py`)
   - PM2 process status checking
   - API connectivity tests (Gmail, Odoo)
   - Disk/memory/CPU monitoring
   - Alert thresholds

2. **Auto-Recovery** (`deploy/cloud/ecosystem.config.js`)
   - PM2 configuration for watchers + orchestrator
   - Auto-restart on crash
   - Max restart attempts
   - Log rotation

3. **Health Status File** (`AI_Employee_Vault/Health/status.md`)
   - Last check timestamp
   - Process status (running/stopped/restarting)
   - Resource usage
   - Recent incidents

### Phase 5: Security Hardening (P2)

1. **.gitignore Audit**
   - Verify all secrets excluded
   - Add cloud-specific exclusions
   - Test sync excludes credentials

2. **Cloud Environment Variables**
   - Minimal secrets (Anthropic API key, Gmail API)
   - No payment credentials
   - No WhatsApp session

3. **Audit Enhancement**
   - Log all cloud actions with `agent_id=cloud`
   - Log all sync operations
   - 90-day retention verification

### Phase 6: Integration Testing (P2)

1. **Platinum Demo Flow Test**
   - Email arrives while local offline
   - Cloud drafts response, syncs
   - Local comes online, pulls
   - User approves, local sends
   - Action logged, moved to Done

2. **Conflict Resolution Test**
   - Both agents claim same task
   - First mover wins
   - Loser detects conflict

3. **Offline Resilience Test**
   - Cloud continues when local offline
   - Local continues when cloud offline
   - Both recover on reconnection

## Dependencies & Prerequisites

### Gold Tier (Required)
- [x] Odoo integration working locally
- [x] CEO Briefing skill
- [x] Social media MCP (draft capability)
- [x] Ralph Wiggum loop
- [x] All watchers functional

### External Requirements
- [ ] Oracle Cloud account with Free Tier
- [ ] GitHub repository for vault sync
- [ ] Domain name for HTTPS (or use VM IP with self-signed)
- [ ] Let's Encrypt SSL certificate
- [ ] PM2 installation on cloud VM

## Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Git sync conflicts | Medium | Medium | Claim-by-move prevents most; conflict resolution docs |
| Secret exposure | Low | Critical | Strict .gitignore; pre-commit hooks; audit |
| Cloud VM unavailable | Low | High | Health alerts; local continues operating |
| Odoo backup failure | Medium | High | Multiple backup destinations; weekly verify |
| Cost overrun | Low | Medium | Oracle Free Tier; monitor usage |
| WhatsApp session expires | Medium | Low | Local-only; manual re-auth documented |

## Success Criteria Mapping

| Success Criteria | Implementation | Verification |
|-----------------|----------------|--------------|
| SC-001: 99.5% cloud uptime | PM2 + health monitor + auto-restart | Uptime monitoring dashboard |
| SC-002: <5 min draft response | Cloud watcher + sync timing | Integration test with timestamps |
| SC-003: <30s vault sync | Git push frequency | Sync latency monitoring |
| SC-004: <60s approval to action | Local pull + approval watcher | End-to-end timing test |
| SC-005: Zero secret exposure | .gitignore + pre-commit hook | Security audit test |
| SC-006: Zero data loss | Git versioning + Odoo backup | Backup restore test |
| SC-007: Work-zone enforcement | Cloud MCP block + local execution | Work-zone integration test |
| SC-008: Platinum demo flow | End-to-end handoff test | Manual + automated demo |

## Next Steps

1. Run `/sp.tasks` to generate actionable task list
2. Create feature branch `002-platinum-tier` (already exists)
3. Implement Phase 1 (Cloud Infrastructure) first as foundation
4. Implement Phase 2 (Vault Sync) to enable Cloud/Local communication
5. Implement Phase 3-4 in parallel (Work-Zone + Health Monitoring)
6. Complete Phase 5-6 (Security + Testing) before demo

---

**Plan Status**: COMPLETE - Ready for Phase 0 research to resolve unknowns, then `/sp.tasks` for implementation tasks.
