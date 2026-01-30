# Tasks: Platinum Tier - Always-On Cloud + Local Executive

**Input**: Design documents from `/specs/002-platinum-tier/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Test tasks are included for critical integration scenarios per the specification requirements.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Source**: `src/` at repository root
- **Tests**: `tests/` at repository root
- **Deploy**: `deploy/` at repository root
- **Vault**: `AI_Employee_Vault/` at repository root

---

## Phase 1: Setup (Cloud Infrastructure Foundation)

**Purpose**: Cloud VM provisioning and basic infrastructure setup

- [X] T001 Create cloud deployment directory structure per plan in deploy/cloud/
- [X] T002 [P] Create VM setup script in deploy/cloud/setup-cloud-vm.sh
- [X] T003 [P] Create PM2 ecosystem configuration in deploy/cloud/ecosystem.config.js
- [X] T004 [P] Create nginx reverse proxy configuration in deploy/cloud/nginx.conf
- [X] T005 [P] Create Docker Compose for Odoo deployment in deploy/cloud/docker-compose.yml
- [X] T006 [P] Create Odoo configuration file in deploy/cloud/odoo.conf
- [X] T007 [P] Create backup cron script in deploy/cloud/backup-cron.sh
- [X] T008 Create local sync setup script in deploy/local/setup-local-sync.sh
- [X] T009 Update .gitignore with cloud-specific exclusions per research.md security requirements
- [X] T010 Create cloud-specific .env.example in deploy/cloud/.env.example

---

## Phase 2: Foundational (Core Distributed Agent Infrastructure)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Data Models

- [X] T011 [P] Create AgentIdentity model in src/models/agent_identity.py
- [X] T012 [P] Create TaskClaim model in src/models/task_claim.py
- [X] T013 [P] Create SyncState model in src/models/sync_state.py
- [X] T014 [P] Create HealthStatus model in src/models/health_status.py
- [X] T015 [P] Create UpdateFile model in src/models/update_file.py
- [X] T016 Extend LoopState model with agent_id and sync_required fields in src/models/loop_state.py
- [X] T017 Extend ApprovalRequest with source_agent and requires_local_action fields in src/models/approval_request.py

### Core Utilities

- [X] T018 Create claim-by-move lock implementation in src/utils/claim_lock.py
- [X] T019 Create WorkZone enum and requires_local decorator in src/cloud/work_zone.py

### Vault Folder Structure

- [X] T020 Create domain subfolders in AI_Employee_Vault/Needs_Action/ (email, accounting, social, local)
- [X] T021 [P] Create domain subfolders in AI_Employee_Vault/Pending_Approval/ (email, accounting, social, payments)
- [X] T022 [P] Create agent subfolders in AI_Employee_Vault/In_Progress/ (cloud, local)
- [X] T023 [P] Create AI_Employee_Vault/Updates/ folder for cloud-written updates
- [X] T024 [P] Create AI_Employee_Vault/Signals/ folder for inter-agent communication
- [X] T025 [P] Create AI_Employee_Vault/Health/ folder with initial status.md template

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 4 - Vault Synchronization (Priority: P0) 🎯 MVP

**Goal**: Git-based vault synchronization between cloud and local agents with claim-by-move task ownership

**Independent Test**: Cloud agent can push changes, local agent can pull and merge, claim conflicts are resolved correctly

**Why First**: All other user stories depend on working vault synchronization

### Tests for US4

- [X] T026 [P] [US4] Contract test for sync protocol in tests/contract/test_sync_protocol.py
- [X] T027 [P] [US4] Integration test for claim-by-move in tests/integration/test_claim_by_move.py
- [X] T028 [P] [US4] Integration test for conflict resolution in tests/integration/test_conflict_resolution.py

### Implementation for US4

- [X] T029 [US4] Create SyncManager class for Git operations in src/cloud/sync_manager.py
- [X] T030 [US4] Implement claim_task method with atomic Git operations in src/utils/claim_lock.py
- [X] T031 [US4] Implement release_task method for task completion in src/utils/claim_lock.py
- [X] T032 [US4] Implement push_changes method in src/cloud/sync_manager.py
- [X] T033 [US4] Implement pull_changes method with conflict detection in src/cloud/sync_manager.py
- [X] T034 [US4] Create SyncPuller for local agent in src/local/sync_puller.py
- [X] T035 [US4] Create DashboardMerger to merge /Updates into Dashboard.md in src/local/dashboard_merger.py
- [X] T036 [US4] Create sync_state.json writer for Health folder in src/cloud/sync_manager.py
- [X] T037 [US4] Add validation and error handling for sync operations
- [X] T038 [US4] Add audit logging for all sync operations

**Checkpoint**: Vault synchronization complete - cloud and local can communicate via Git

---

## Phase 4: User Story 3 - Work-Zone Specialization (Priority: P0)

**Goal**: Clear boundaries between cloud (draft-only) and local (execution) capabilities

**Independent Test**: Cloud agent is blocked from executing send/post/pay actions; local agent can execute all actions

### Tests for US3

- [X] T039 [P] [US3] Contract test for work-zone enforcement in tests/contract/test_work_zone.py
- [X] T040 [P] [US3] Integration test for cloud blocked actions in tests/integration/test_cloud_local_handoff.py

### Implementation for US3

- [X] T041 [US3] Complete WorkZone enforcer with cloud-allowed and cloud-blocked lists in src/cloud/work_zone.py
- [X] T042 [US3] Add @requires_local decorator to email_mcp.send_email in src/mcp_servers/email_mcp.py
- [X] T043 [US3] Add @requires_local decorator to social_mcp.post methods in src/mcp_servers/social_mcp.py
- [X] T044 [US3] Add @requires_local decorator to odoo_mcp.post_invoice and post_payment in src/mcp_servers/odoo_mcp.py
- [X] T045 [US3] Create draft-only wrappers for cloud MCP operations in src/cloud/work_zone.py
- [X] T046 [US3] Add work-zone violation audit logging in src/cloud/work_zone.py
- [X] T047 [US3] Update Company_Handbook.md with work-zone boundaries documentation

**Checkpoint**: Work-zone enforcement complete - cloud cannot execute sensitive actions

---

## Phase 5: User Story 1 - Cloud Email Triage (Priority: P1)

**Goal**: Cloud agent triages emails and creates draft responses while user is away

**Independent Test**: Email arrives, cloud creates draft in Pending_Approval/email/, syncs via Git

### Tests for US1

- [X] T048 [P] [US1] Integration test for email triage flow in tests/integration/test_email_triage.py

### Implementation for US1

- [X] T049 [US1] Create email triage skill in src/skills/email_triage.py
- [X] T050 [US1] Implement priority categorization (urgent/normal/low) in email triage skill
- [X] T051 [US1] Implement draft response generation in email triage skill
- [X] T052 [US1] Create email summary generator for /Updates/email_summary.md in src/skills/email_triage.py
- [X] T053 [US1] Integrate email triage skill with cloud orchestrator
- [X] T054 [US1] Add email triage audit logging

**Checkpoint**: Email triage complete - drafts created and synced for approval

---

## Phase 6: User Story 2 - Cloud Social Media Scheduling (Priority: P1)

**Goal**: Cloud agent drafts social media posts without publishing

**Independent Test**: Scheduled post time approaches, cloud creates draft in Pending_Approval/social/, local can approve and publish

### Tests for US2

- [X] T055 [P] [US2] Integration test for social media draft flow in tests/integration/test_social_draft.py

### Implementation for US2

- [X] T056 [US2] Create social media draft skill in src/skills/social_draft.py
- [X] T057 [US2] Implement post scheduling check in social draft skill
- [X] T058 [US2] Create draft post file writer to Pending_Approval/social/ in src/skills/social_draft.py
- [X] T059 [US2] Integrate social draft skill with cloud orchestrator
- [X] T060 [US2] Add social draft audit logging

**Checkpoint**: Social media drafting complete - posts ready for local approval

---

## Phase 7: User Story 5 - Cloud Odoo Integration (Priority: P1)

**Goal**: Cloud agent creates draft invoices in Odoo without posting

**Independent Test**: Invoice request received, cloud creates draft invoice in Odoo, approval request in Pending_Approval/accounting/

### Tests for US5

- [X] T061 [P] [US5] Integration test for Odoo draft invoice flow in tests/integration/test_odoo_draft.py

### Implementation for US5

- [X] T062 [US5] Create cloud-safe Odoo MCP wrapper for draft-only operations in src/cloud/cloud_odoo_mcp.py
- [X] T063 [US5] Implement create_draft_invoice method (never posts) in cloud Odoo MCP
- [X] T064 [US5] Create approval request writer for accounting domain in src/cloud/cloud_odoo_mcp.py
- [X] T065 [US5] Integrate cloud Odoo MCP with cloud orchestrator
- [X] T066 [US5] Add Odoo draft operation audit logging

**Checkpoint**: Odoo drafting complete - invoices ready for local posting

---

## Phase 8: User Story 6 - Health Monitoring (Priority: P1)

**Goal**: Comprehensive health monitoring for cloud agent with auto-recovery

**Independent Test**: Process crashes, watchdog detects and restarts within 60 seconds, incident logged

### Tests for US6

- [X] T067 [P] [US6] Unit test for health monitor in tests/unit/test_health_monitor.py
- [X] T068 [P] [US6] Integration test for auto-recovery in tests/integration/test_auto_recovery.py

### Implementation for US6

- [X] T069 [US6] Create HealthMonitor class in src/cloud/health_monitor.py
- [X] T070 [US6] Implement check_process method for PM2 status in src/cloud/health_monitor.py
- [X] T071 [US6] Implement check_api method for Gmail and Odoo connectivity in src/cloud/health_monitor.py
- [X] T072 [US6] Implement get_resources method for CPU/memory/disk in src/cloud/health_monitor.py
- [X] T073 [US6] Implement restart_process method via PM2 in src/cloud/health_monitor.py
- [X] T074 [US6] Implement send_alert method for critical failures in src/cloud/health_monitor.py
- [X] T075 [US6] Create status.md writer for Health folder in src/cloud/health_monitor.py
- [X] T076 [US6] Add health check interval loop (60 seconds) in src/cloud/health_monitor.py
- [X] T077 [US6] Add incident logging to vault in src/cloud/health_monitor.py

**Checkpoint**: Health monitoring complete - auto-recovery and alerting active

---

## Phase 9: Cloud and Local Orchestrators

**Goal**: Main entry points for cloud and local agents

**Independent Test**: Cloud orchestrator starts watchers and processes inbox in draft-only mode; local orchestrator processes approvals

### Tests for Orchestrators

- [X] T078 [P] Unit test for cloud orchestrator in tests/unit/test_cloud_orchestrator.py
- [X] T079 [P] Unit test for local orchestrator in tests/unit/test_local_orchestrator.py

### Implementation for Orchestrators

- [X] T080 Create CloudOrchestrator class in src/cloud/cloud_orchestrator.py
- [X] T081 Implement cloud watcher loading (gmail, filesystem, odoo_monitor) in cloud orchestrator
- [X] T082 Implement draft-only MCP enforcement in cloud orchestrator
- [X] T083 Implement Git sync after each task in cloud orchestrator
- [X] T084 Create LocalOrchestrator class extending base orchestrator in src/local/local_orchestrator.py
- [X] T085 Implement Git pull on startup in local orchestrator
- [X] T086 Implement periodic Git pull (every 60s) in local orchestrator
- [X] T087 Integrate DashboardMerger with local orchestrator
- [X] T088 Implement approval processing in local orchestrator
- [X] T089 Add cloud orchestrator entry point script in src/cloud/__main__.py
- [X] T090 Add local orchestrator entry point script in src/local/__main__.py

**Checkpoint**: Both orchestrators ready - agents can run independently

---

## Phase 10: User Story 7 - Platinum Demo Flow (Priority: P2)

**Goal**: End-to-end demo of Cloud/Local handoff for hackathon

**Independent Test**: Complete flow: email arrives → cloud drafts → syncs → local approves → sends → logged

### Tests for US7

- [X] T091 [US7] End-to-end integration test for platinum demo in tests/integration/test_platinum_demo.py

### Implementation for US7

- [X] T092 [US7] Create demo setup script in deploy/demo/setup_demo.sh
- [X] T093 [US7] Create demo scenario with sample email in deploy/demo/sample_email.md
- [ ] T094 [US7] Document demo flow in docs/PLATINUM_DEMO.md
- [X] T095 [US7] Verify all components work together for demo scenario

**Checkpoint**: Demo ready for hackathon presentation

---

## Phase 11: Polish & Security Hardening

**Purpose**: Security, documentation, and cross-cutting improvements

### Security

- [X] T096 [P] Audit .gitignore for secret exclusions
- [ ] T097 [P] Create pre-commit hook for secret detection in .git/hooks/pre-commit
- [X] T098 Test vault sync excludes all credential files
- [X] T099 Verify cloud .env has minimal secrets per research.md

### Documentation

- [ ] T100 [P] Update CLAUDE.md with Platinum tier documentation
- [ ] T101 [P] Create deployment guide in docs/DEPLOYMENT.md
- [ ] T102 [P] Create troubleshooting guide in docs/TROUBLESHOOTING.md
- [X] T103 [P] Update Company_Handbook.md with cloud/local operational rules

### Final Validation

- [X] T104 Run quickstart.md validation for Platinum tier
- [X] T105 Verify 99.5% uptime monitoring is active
- [X] T106 Verify <30s sync latency target is met
- [X] T107 Verify <5min draft response time is met

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 completion - BLOCKS all user stories
- **Phase 3 (US4 Vault Sync)**: Depends on Phase 2 - ALL other stories depend on this
- **Phase 4 (US3 Work-Zone)**: Depends on Phase 3 - Required for safe cloud operation
- **Phase 5-8 (US1, US2, US5, US6)**: Depend on Phase 4 - Can proceed in parallel
- **Phase 9 (Orchestrators)**: Depends on Phase 4-8 components being ready
- **Phase 10 (US7 Demo)**: Depends on Phase 9 completion
- **Phase 11 (Polish)**: Depends on all previous phases

### User Story Dependencies

```
US4 (Vault Sync) - P0 Foundation
    ↓
US3 (Work-Zone) - P0 Required for cloud safety
    ↓
    ├── US1 (Email Triage) - P1 Independent
    ├── US2 (Social Drafts) - P1 Independent
    ├── US5 (Odoo Drafts) - P1 Independent
    └── US6 (Health Monitor) - P1 Independent
            ↓
        US7 (Demo Flow) - P2 Requires all above
```

### Within Each User Story

- Tests written FIRST and FAIL before implementation
- Models before services
- Services before skills
- Skills before orchestrator integration
- Audit logging at each layer

### Parallel Opportunities

**Phase 1 (Setup)**: T002-T007 can all run in parallel
**Phase 2 (Models)**: T011-T015 can all run in parallel
**Phase 2 (Folders)**: T020-T025 can all run in parallel
**Phase 3 (US4 Tests)**: T026-T028 can all run in parallel
**Phase 5-8**: User Stories 1, 2, 5, 6 can all run in parallel after Phase 4
**Phase 11 (Docs)**: T100-T103 can all run in parallel

---

## Parallel Example: Phase 2 Models

```bash
# Launch all model tasks together:
Task: "Create AgentIdentity model in src/models/agent_identity.py"
Task: "Create TaskClaim model in src/models/task_claim.py"
Task: "Create SyncState model in src/models/sync_state.py"
Task: "Create HealthStatus model in src/models/health_status.py"
Task: "Create UpdateFile model in src/models/update_file.py"
```

## Parallel Example: Phase 5-8 User Stories

```bash
# After Phase 4 completes, launch all P1 user stories together:
Team Member A: "User Story 1 - Email Triage (T048-T054)"
Team Member B: "User Story 2 - Social Drafts (T055-T060)"
Team Member C: "User Story 5 - Odoo Drafts (T061-T066)"
Team Member D: "User Story 6 - Health Monitor (T067-T077)"
```

---

## Implementation Strategy

### MVP First (Vault Sync + Work-Zone + One Story)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US4 Vault Sync
4. Complete Phase 4: US3 Work-Zone
5. Complete Phase 5: US1 Email Triage
6. **STOP and VALIDATE**: Test cloud/local handoff end-to-end
7. Deploy/demo if ready (minimal viable Platinum tier)

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US4 (Vault Sync) → Test sync → Core communication working
3. Add US3 (Work-Zone) → Test enforcement → Safe for cloud operation
4. Add US1 (Email Triage) → Test independently → Email demo ready
5. Add US2 (Social Drafts) → Test independently → Social demo ready
6. Add US5 (Odoo Drafts) → Test independently → Accounting demo ready
7. Add US6 (Health Monitor) → Test independently → 99.5% uptime
8. Add US7 (Demo Flow) → Full platinum demo

### Single Developer Path

Week 1: Phase 1-2 (Setup + Foundation)
Week 2: Phase 3-4 (US4 Vault Sync + US3 Work-Zone)
Week 3: Phase 5-6 (US1 Email Triage + US2 Social Drafts)
Week 4: Phase 7-8 (US5 Odoo Drafts + US6 Health Monitor)
Week 5: Phase 9-11 (Orchestrators + Demo + Polish)

---

## Summary

| Metric | Count |
|--------|-------|
| **Total Tasks** | 107 |
| **Phase 1 (Setup)** | 10 tasks |
| **Phase 2 (Foundational)** | 15 tasks |
| **US4 (Vault Sync)** | 13 tasks |
| **US3 (Work-Zone)** | 9 tasks |
| **US1 (Email Triage)** | 7 tasks |
| **US2 (Social Drafts)** | 6 tasks |
| **US5 (Odoo Drafts)** | 6 tasks |
| **US6 (Health Monitor)** | 11 tasks |
| **Orchestrators** | 13 tasks |
| **US7 (Demo)** | 5 tasks |
| **Polish** | 12 tasks |

### MVP Scope (Recommended)

For minimum viable Platinum tier, complete through Phase 5 (US1 Email Triage):
- **Tasks**: T001-T054 (54 tasks)
- **Result**: Working cloud/local sync with email triage demo

### Parallel Opportunities

- **45 tasks** marked with [P] can run in parallel within their phases
- **User Stories 1, 2, 5, 6** can all execute in parallel after Work-Zone phase

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable (after dependencies)
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- Gold Tier must be complete before starting Platinum Tier
