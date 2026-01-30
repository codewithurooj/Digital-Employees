# Tasks: Gold Tier - Autonomous Employee

**Input**: Design documents from `/specs/001-gold-tier/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL - included only for critical paths as specified in the feature.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Vault folder: `AI_Employee_Vault/`
- Skills: `.claude/commands/`
- Config: `config/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and Gold Tier configuration

- [ ] T001 Create Gold Tier folder structure per plan.md in src/mcp_servers/, src/lib/, src/skills/
- [ ] T002 [P] Add Gold Tier dependencies to requirements.txt (playwright, schedule)
- [ ] T003 [P] Create .env.example with Gold Tier variables (ODOO_*, FACEBOOK_*, TWITTER_*, BRIEFING_*)
- [ ] T004 [P] Create vault accounting folder structure AI_Employee_Vault/Accounting/{Invoices,Payments,Transactions}/
- [ ] T005 [P] Create vault social folder structure AI_Employee_Vault/Social/{Drafts,Metrics}/
- [ ] T006 [P] Create vault briefings folder AI_Employee_Vault/Briefings/
- [ ] T007 Update config/orchestrator.yaml with Gold Tier MCP servers and scheduled tasks

**Checkpoint**: Project structure ready for Gold Tier implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Create OdooConnection config schema in config/odoo_config.json per data-model.md
- [ ] T009 [P] Create base SocialPost Pydantic model in src/models/social_post.py per data-model.md
- [ ] T010 [P] Create base Invoice Pydantic model in src/models/invoice.py per data-model.md
- [ ] T011 [P] Create base Payment Pydantic model in src/models/payment.py per data-model.md
- [ ] T012 [P] Create base Transaction Pydantic model in src/models/transaction.py per data-model.md
- [ ] T013 [P] Create base Engagement Pydantic model in src/models/engagement.py per data-model.md
- [ ] T014 [P] Create CEOBriefing Pydantic model in src/models/ceo_briefing.py per data-model.md
- [ ] T015 [P] Create LoopState enhanced model with pause/resume in src/models/loop_state.py per data-model.md
- [ ] T016 Implement audit logging to JSONL format in src/utils/audit_logger.py per research.md

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Odoo Accounting Integration (Priority: P1)

**Goal**: Integrate with Odoo to track invoices, payments, and financial transactions automatically

**Independent Test**: Create a test invoice in Odoo, verify AI Employee detects and logs it to vault

### Implementation for User Story 1

- [ ] T017 [US1] Implement OdooClient class with XML-RPC auth in src/lib/odoo_client.py
- [ ] T018 [US1] Add authenticate() method to OdooClient with database/user/apikey
- [ ] T019 [US1] Add search_invoices() method to OdooClient for account.move model
- [ ] T020 [US1] Add search_payments() method to OdooClient for account.payment model
- [ ] T021 [US1] Add get_account_balances() method to OdooClient
- [ ] T022 [US1] Add test_connection() health check method to OdooClient
- [ ] T023 [US1] Implement retry logic with exponential backoff in OdooClient
- [ ] T024 [US1] Implement OdooWatcher class extending BaseWatcher in src/watchers/odoo_watcher.py
- [ ] T025 [US1] Add poll_invoices() method to OdooWatcher with sync_interval support
- [ ] T026 [US1] Add poll_payments() method to OdooWatcher
- [ ] T027 [US1] Implement action file creation in Needs_Action for new invoices/payments
- [ ] T028 [US1] Add graceful degradation when Odoo unavailable (circuit breaker integration)
- [ ] T029 [US1] Implement OdooMCP server class in src/mcp_servers/odoo_mcp.py
- [ ] T030 [US1] Implement /health endpoint per odoo-mcp.yaml contract
- [ ] T031 [US1] Implement /sync/invoices endpoint per odoo-mcp.yaml contract
- [ ] T032 [US1] Implement /sync/payments endpoint per odoo-mcp.yaml contract
- [ ] T033 [US1] Implement /invoices/draft endpoint per odoo-mcp.yaml contract
- [ ] T034 [US1] Implement /accounts/balance endpoint per odoo-mcp.yaml contract
- [ ] T035 [US1] Implement /transactions/daily endpoint per odoo-mcp.yaml contract
- [ ] T036 [US1] Add invoice-to-markdown converter for vault storage
- [ ] T037 [US1] Add payment-to-markdown converter for vault storage
- [ ] T038 [US1] Add daily transaction log generator for vault
- [ ] T039 [US1] Register OdooMCP in orchestrator with rate limit (100/hr) and circuit breaker
- [ ] T040 [US1] Add audit logging for all Odoo operations

**Checkpoint**: Odoo integration complete - can sync invoices/payments to vault independently

---

## Phase 4: User Story 2 - Weekly CEO Briefing Generation (Priority: P1)

**Goal**: Generate weekly CEO briefing summarizing revenue, tasks, bottlenecks, and suggestions

**Independent Test**: Run briefing generator with sample data, verify structured report in Briefings/

### Implementation for User Story 2

- [ ] T041 [P] [US2] Implement revenue aggregator reading Accounting/Invoices/ in src/skills/ceo_briefing.py
- [ ] T042 [P] [US2] Implement expense aggregator reading Accounting/Payments/ in src/skills/ceo_briefing.py
- [ ] T043 [P] [US2] Implement task completion scanner reading Done/ folder
- [ ] T044 [P] [US2] Implement bottleneck detector scanning Needs_Action/ for age > 48h
- [ ] T045 [US2] Implement Business_Goals.md parser for target comparison
- [ ] T046 [US2] Implement suggestion generator for cost optimization patterns
- [ ] T047 [US2] Implement CEOBriefingSkill class following skill pattern in src/skills/ceo_briefing.py
- [ ] T048 [US2] Implement generate_briefing() method per briefing-skill.yaml contract
- [ ] T049 [US2] Implement get_revenue_summary() method per contract
- [ ] T050 [US2] Implement get_task_summary() method per contract
- [ ] T051 [US2] Implement get_bottlenecks() method per contract
- [ ] T052 [US2] Implement generate_suggestions() method per contract
- [ ] T053 [US2] Implement briefing-to-markdown converter for vault
- [ ] T054 [US2] Create CEO briefing skill definition in .claude/commands/ceo-briefing.md
- [ ] T055 [US2] Add scheduled trigger in orchestrator (Sunday 11 PM cron)
- [ ] T056 [US2] Add 10-minute timeout handling with partial report fallback
- [ ] T057 [US2] Add audit logging for briefing generation

**Checkpoint**: CEO Briefing complete - generates weekly reports from vault data independently

---

## Phase 5: User Story 3 - Facebook & Instagram Integration (Priority: P2)

**Goal**: Post content to Facebook/Instagram with approval workflow and engagement tracking

**Independent Test**: Draft a post for Facebook, approve it, verify publication and logging

### Implementation for User Story 3

- [ ] T058 [P] [US3] Implement FacebookClient class in src/lib/social_clients/facebook.py
- [ ] T059 [P] [US3] Implement InstagramClient class in src/lib/social_clients/instagram.py
- [ ] T060 [US3] Add Graph API authentication to FacebookClient
- [ ] T061 [US3] Add Graph API authentication to InstagramClient
- [ ] T062 [US3] Implement create_post() for Facebook text/image posts
- [ ] T063 [US3] Implement create_post() for Instagram with image requirement validation
- [ ] T064 [US3] Implement get_engagement() for Facebook (reach, likes, shares)
- [ ] T065 [US3] Implement get_engagement() for Instagram (reach, likes, saves)
- [ ] T066 [US3] Add Playwright fallback handler in src/lib/social_clients/browser_fallback.py
- [ ] T067 [US3] Implement content validation for character limits (FB 63206, IG 2200)
- [ ] T068 [US3] Implement image dimension validation for Instagram (320x320 min)
- [ ] T069 [US3] Add rate limit tracking (FB 200/hr, IG 25 posts/day)
- [ ] T070 [US3] Implement draft-to-markdown converter for Social/Drafts/
- [ ] T071 [US3] Implement engagement-to-markdown converter for Social/Metrics/

**Checkpoint**: Facebook/Instagram clients ready - can draft, validate, and post content

---

## Phase 6: User Story 4 - Twitter/X Integration (Priority: P2)

**Goal**: Post content to Twitter/X with character validation and mention monitoring

**Independent Test**: Draft a tweet, approve it, verify publication with URL logged

### Implementation for User Story 4

- [ ] T072 [P] [US4] Implement TwitterClient class in src/lib/social_clients/twitter.py
- [ ] T073 [US4] Add API v2 OAuth 2.0 authentication to TwitterClient
- [ ] T074 [US4] Implement create_tweet() with 280 character validation
- [ ] T075 [US4] Implement thread creation for >280 character content
- [ ] T076 [US4] Implement get_engagement() for Twitter (impressions, retweets, likes)
- [ ] T077 [US4] Add Playwright fallback for Twitter
- [ ] T078 [US4] Implement mention/keyword monitoring in TwitterClient
- [ ] T079 [US4] Add action file creation for keyword matches in Needs_Action
- [ ] T080 [US4] Add rate limit tracking (1500 tweets/month free tier)

**Checkpoint**: Twitter client ready - can post tweets and monitor mentions

---

## Phase 7: User Story 3+4 Combined - Social Media MCP Server (Priority: P2)

**Goal**: Unified MCP server for all social platforms with approval workflows

**Independent Test**: Verify each platform health check independently

### Implementation for Combined Social Stories

- [ ] T081 [US3] [US4] Implement SocialMCP server class in src/mcp_servers/social_mcp.py
- [ ] T082 [US3] [US4] Implement /health endpoint with per-platform status per social-mcp.yaml
- [ ] T083 [US3] [US4] Implement /posts/draft endpoint per social-mcp.yaml contract
- [ ] T084 [US3] [US4] Implement /posts/validate endpoint per social-mcp.yaml contract
- [ ] T085 [US3] [US4] Implement /posts/{draft_id}/publish endpoint per social-mcp.yaml contract
- [ ] T086 [US3] [US4] Implement /posts/{post_id}/engagement endpoint per social-mcp.yaml contract
- [ ] T087 [US3] [US4] Implement /platforms/{platform}/status endpoint per social-mcp.yaml
- [ ] T088 [US3] [US4] Integrate HITL approval workflow for all posts
- [ ] T089 [US3] [US4] Create social posting skill definition in .claude/commands/social-posting.md
- [ ] T090 [US3] [US4] Implement SocialPostingSkill class in src/skills/social_posting.py
- [ ] T091 [US3] [US4] Register SocialMCP in orchestrator with rate limit (5/day) and circuit breaker
- [ ] T092 [US3] [US4] Add audit logging for all social media operations

**Checkpoint**: Social Media MCP complete - all platforms accessible through unified API

---

## Phase 8: User Story 5 - Ralph Wiggum Loop Enhancement (Priority: P2)

**Goal**: Enable pause/resume for multi-step tasks requiring mid-loop approvals

**Independent Test**: Start multi-step task, trigger approval pause, approve, verify resume

### Implementation for User Story 5

- [ ] T093 [US5] Enhance LoopState class with save() method in src/utils/ralph_wiggum.py
- [ ] T094 [US5] Implement load() classmethod for state deserialization
- [ ] T095 [US5] Add pause_for_approval() method that serializes state to vault
- [ ] T096 [US5] Add resume_from_state() method that loads and continues
- [ ] T097 [US5] Implement approval callback integration in loop
- [ ] T098 [US5] Add state file watcher for approval completion detection
- [ ] T099 [US5] Implement graceful abort on approval rejection
- [ ] T100 [US5] Add loop state file cleanup after completion
- [ ] T101 [US5] Update orchestrator to handle paused loops on restart
- [ ] T102 [US5] Add audit logging for loop state transitions

**Checkpoint**: Ralph Wiggum loop supports pause/resume - complex workflows complete autonomously

---

## Phase 9: User Story 6 - Multiple MCP Servers (Priority: P3)

**Goal**: Properly isolated MCP servers with independent health checks

**Independent Test**: Verify each MCP server health check responds independently

### Implementation for User Story 6

- [ ] T103 [US6] Update orchestrator for multi-MCP server registration in orchestrator.py
- [ ] T104 [US6] Implement independent health check polling for each MCP server
- [ ] T105 [US6] Implement circuit breaker isolation per MCP server
- [ ] T106 [US6] Add MCP server status to Dashboard.md
- [ ] T107 [US6] Implement MCP server restart on health check failure
- [ ] T108 [US6] Add audit logging for MCP server state changes

**Checkpoint**: Multi-MCP architecture complete - servers operate independently

---

## Phase 10: User Story 7 - Comprehensive Audit Logging (Priority: P3)

**Goal**: Structured JSON audit logs with 90-day retention

**Independent Test**: Perform any action, verify log entry in Logs/ with correct format

### Implementation for User Story 7

- [ ] T109 [US7] Finalize JSONL log format in src/utils/audit_logger.py per research.md
- [ ] T110 [US7] Implement daily log rotation (Logs/YYYY-MM-DD.jsonl)
- [ ] T111 [US7] Add log entry fields: timestamp, action_type, component, actor, target, parameters
- [ ] T112 [US7] Add approval_status and result fields to log entries
- [ ] T113 [US7] Implement 90-day retention cleanup job
- [ ] T114 [US7] Add retention cleanup to orchestrator scheduled tasks
- [ ] T115 [US7] Create log query utility for date-based retrieval

**Checkpoint**: Audit logging complete - all actions traceable with 90-day retention

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Final integration and validation across all stories

- [ ] T116 [P] Update quickstart.md with verified setup commands
- [ ] T117 [P] Create troubleshooting section in docs for common issues
- [ ] T118 Run full integration test: Odoo sync → CEO briefing → verify data flow
- [ ] T119 Run full integration test: Social post draft → approve → publish → engagement
- [ ] T120 Run full integration test: Ralph Wiggum multi-step with approval pause
- [ ] T121 Verify rate limits across all MCP servers
- [ ] T122 Verify circuit breakers isolate failures correctly
- [ ] T123 Verify audit logs capture all actions
- [ ] T124 Security review: verify no secrets in vault files
- [ ] T125 Performance test: 50+ Odoo transactions/day per SC-007

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - Odoo integration is P1
- **User Story 2 (Phase 4)**: Depends on Foundational + US1 (needs accounting data)
- **User Stories 3+4 (Phases 5-7)**: Depend on Foundational - can parallel with US1/US2
- **User Story 5 (Phase 8)**: Depends on Foundational - can parallel with others
- **User Stories 6+7 (Phases 9-10)**: Depend on Foundational - can parallel with others
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (Odoo)**: Independent after Foundational
- **US2 (CEO Briefing)**: Depends on US1 for accounting data (can use mock data for early testing)
- **US3 (Facebook/Instagram)**: Independent after Foundational
- **US4 (Twitter)**: Independent after Foundational
- **US5 (Ralph Wiggum)**: Independent after Foundational
- **US6 (Multi-MCP)**: Should implement after at least 2 MCP servers exist
- **US7 (Audit Logging)**: Independent after Foundational (started in T016)

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational model tasks (T009-T015) can run in parallel
- US3 and US4 (social platforms) can be developed in parallel
- US5 (Ralph Wiggum) can be developed in parallel with social stories
- Within each story, tasks marked [P] can run in parallel

---

## Parallel Example: Foundational Models

```bash
# Launch all model creations together:
Task: "Create base SocialPost model in src/models/social_post.py"
Task: "Create base Invoice model in src/models/invoice.py"
Task: "Create base Payment model in src/models/payment.py"
Task: "Create base Transaction model in src/models/transaction.py"
Task: "Create base Engagement model in src/models/engagement.py"
Task: "Create CEOBriefing model in src/models/ceo_briefing.py"
Task: "Create LoopState enhanced model in src/models/loop_state.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (Odoo Integration)
4. Complete Phase 4: User Story 2 (CEO Briefing)
5. **STOP and VALIDATE**: Test Odoo sync + CEO briefing flow
6. Deploy/demo - business value delivered!

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 (Odoo) → Test independently → Deploy (accounting visibility!)
3. Add US2 (CEO Briefing) → Test independently → Deploy (weekly intelligence!)
4. Add US3+US4 (Social Media) → Test independently → Deploy (social presence!)
5. Add US5 (Ralph Wiggum) → Test independently → Deploy (full autonomy!)
6. Add US6+US7 (Infrastructure) → Test independently → Deploy (enterprise-ready!)

### Suggested MVP Scope

**MVP = Phase 1 + Phase 2 + Phase 3 + Phase 4** (Setup, Foundational, Odoo, CEO Briefing)

This delivers:
- SC-001: Financial summary without Odoo login
- SC-002: Weekly CEO briefing generation
- SC-006: Audit trail for accounting actions
- SC-007: Handle 50+ transactions/day

---

## Summary

| Phase | Story | Task Count | Description |
|-------|-------|------------|-------------|
| 1 | Setup | 7 | Project structure and config |
| 2 | Foundational | 9 | Core models and audit logging |
| 3 | US1 | 24 | Odoo Accounting Integration |
| 4 | US2 | 17 | CEO Briefing Generation |
| 5 | US3 | 14 | Facebook/Instagram Integration |
| 6 | US4 | 9 | Twitter/X Integration |
| 7 | US3+4 | 12 | Social Media MCP Server |
| 8 | US5 | 10 | Ralph Wiggum Enhancement |
| 9 | US6 | 6 | Multiple MCP Servers |
| 10 | US7 | 7 | Comprehensive Audit Logging |
| 11 | Polish | 10 | Integration and Validation |
| **Total** | | **125** | |

**Parallel Opportunities**: 38 tasks marked [P]
**MVP Task Count**: 57 tasks (Phases 1-4)
**Independent Test Criteria**: Each user story has defined independent test

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All MCP endpoints must match their OpenAPI contracts
- All vault file formats must match data-model.md specifications
