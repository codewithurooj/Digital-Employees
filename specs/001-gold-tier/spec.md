# Feature Specification: Gold Tier - Autonomous Employee

**Feature Branch**: `001-gold-tier`
**Created**: 2026-01-25
**Status**: Draft
**Input**: User description: "write specification for gold tier of the project"

## Overview

The Gold Tier transforms the AI Employee from a functional assistant (Silver Tier) into a fully autonomous employee capable of managing both personal and business affairs. This tier adds accounting integration via Odoo, social media management across multiple platforms (Facebook, Instagram, Twitter/X), weekly business audits with CEO briefings, and autonomous multi-step task completion via the Ralph Wiggum loop.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Odoo Accounting Integration (Priority: P1)

As a business owner, I want the AI Employee to integrate with my Odoo accounting system so that it can track invoices, payments, and financial transactions automatically.

**Why this priority**: Accounting is the backbone of business operations. Without financial visibility, the AI cannot generate meaningful business insights or CEO briefings.

**Independent Test**: Can be fully tested by creating a test invoice in Odoo and verifying the AI Employee can read, categorize, and log the transaction. Delivers immediate value for financial tracking.

**Acceptance Scenarios**:

1. **Given** Odoo is configured with valid credentials, **When** a new invoice is created in Odoo, **Then** the AI Employee detects it within 5 minutes and creates an action file in the vault
2. **Given** a payment is recorded in Odoo, **When** the AI Employee processes accounting data, **Then** the transaction appears in the vault's Accounting folder with correct categorization
3. **Given** the AI Employee needs to create a draft invoice, **When** it submits via Odoo MCP, **Then** the invoice is created in draft status requiring human approval before sending
4. **Given** Odoo is temporarily unavailable, **When** the AI Employee attempts to sync, **Then** it logs the failure, retries with exponential backoff, and queues actions for later

---

### User Story 2 - Weekly CEO Briefing Generation (Priority: P1)

As a business owner, I want the AI Employee to generate a weekly CEO briefing every Monday morning that summarizes revenue, completed tasks, bottlenecks, and proactive suggestions.

**Why this priority**: This is the "Business Handover" feature that transforms the AI from reactive to proactive, providing high-value business intelligence.

**Independent Test**: Can be tested by running the briefing generator with sample accounting and task data, verifying it produces a structured report in the Briefings folder.

**Acceptance Scenarios**:

1. **Given** it is Sunday night at the scheduled time, **When** the audit trigger fires, **Then** the AI Employee reads Business_Goals.md, Done folder tasks, and accounting data
2. **Given** accounting and task data are available, **When** the CEO Briefing is generated, **Then** it includes: revenue summary, completed tasks, bottlenecks, and at least one proactive suggestion
3. **Given** the briefing identifies cost optimization opportunities, **When** presenting suggestions, **Then** each suggestion includes the potential savings amount and an actionable recommendation
4. **Given** the briefing is complete, **When** written to vault, **Then** it appears in Briefings folder with format `YYYY-MM-DD_Monday_Briefing.md`

---

### User Story 3 - Facebook & Instagram Integration (Priority: P2)

As a business owner, I want the AI Employee to post content to Facebook and Instagram and generate engagement summaries so I can maintain social media presence with minimal effort.

**Why this priority**: Social media presence drives business visibility. Automated posting with approval ensures brand consistency.

**Independent Test**: Can be tested by drafting a post for Facebook, approving it, and verifying it publishes correctly with proper logging.

**Acceptance Scenarios**:

1. **Given** Facebook credentials are configured, **When** a post is drafted, **Then** an approval request is created in Pending_Approval with post preview
2. **Given** a post is approved, **When** the AI Employee publishes, **Then** the post appears on Facebook and the action is logged with timestamp and post ID
3. **Given** Instagram credentials are configured, **When** an image post is drafted, **Then** the system validates image dimensions meet Instagram requirements
4. **Given** posts have been published, **When** summary is requested, **Then** engagement metrics (likes, comments, shares) are retrieved and stored in vault

---

### User Story 4 - Twitter/X Integration (Priority: P2)

As a business owner, I want the AI Employee to post content to Twitter/X and monitor relevant mentions so I can engage with my audience efficiently.

**Why this priority**: Twitter/X is essential for real-time business communication and brand presence.

**Independent Test**: Can be tested by drafting a tweet, approving it, and verifying publication with character count validation.

**Acceptance Scenarios**:

1. **Given** Twitter/X credentials are configured, **When** a tweet is drafted exceeding 280 characters, **Then** the system warns and suggests truncation or thread creation
2. **Given** a tweet is approved, **When** published, **Then** the tweet URL and ID are logged in vault
3. **Given** the AI monitors mentions, **When** a keyword match is found, **Then** an action file is created in Needs_Action with context

---

### User Story 5 - Ralph Wiggum Loop for Autonomous Task Completion (Priority: P2)

As a user, I want the AI Employee to continue working on multi-step tasks until completion rather than stopping after each step, so complex tasks are handled autonomously.

**Why this priority**: Enables true autonomous operation where the AI can complete complex workflows without repeated human intervention.

**Independent Test**: Can be tested by starting a multi-step task (e.g., "process all files in Needs_Action and move to Done") and verifying the loop continues until completion or max iterations.

**Acceptance Scenarios**:

1. **Given** a task requires multiple steps, **When** the Ralph Wiggum loop starts, **Then** Claude continues iterating until the task file is moved to Done or max iterations reached
2. **Given** the loop is running, **When** Claude outputs `<promise>TASK_COMPLETE</promise>`, **Then** the loop exits successfully
3. **Given** a loop exceeds max iterations, **When** the limit is reached, **Then** the loop stops gracefully and logs incomplete status
4. **Given** a task requires human approval mid-loop, **When** approval is needed, **Then** the loop pauses, creates approval request, and resumes after approval

---

### User Story 6 - Multiple MCP Servers (Priority: P3)

As a developer, I want the AI Employee to use multiple specialized MCP servers for different action types so each external integration is properly isolated and manageable.

**Why this priority**: Separation of concerns improves reliability and makes debugging easier.

**Independent Test**: Can be tested by verifying each MCP server responds to health checks independently.

**Acceptance Scenarios**:

1. **Given** multiple MCP servers are configured, **When** the orchestrator starts, **Then** each server is initialized and health-checked
2. **Given** one MCP server fails, **When** another server is called, **Then** the functioning server continues to work (circuit breaker isolation)
3. **Given** the email MCP is called, **When** sending an email, **Then** only email-related capabilities are exposed

---

### User Story 7 - Comprehensive Audit Logging (Priority: P3)

As an auditor, I want all AI Employee actions logged in structured JSON format with timestamps so I can review what the system did and when.

**Why this priority**: Accountability and debugging require detailed audit trails.

**Independent Test**: Can be tested by performing any action and verifying log entry appears in Logs folder.

**Acceptance Scenarios**:

1. **Given** any action is performed, **When** logged, **Then** entry includes: ISO 8601 timestamp, action_type, actor, target, parameters, approval_status, result
2. **Given** logs exist, **When** queried by date, **Then** all actions for that day are retrievable from a single JSON file
3. **Given** retention policy is 90 days, **When** logs are older, **Then** they are archived or cleaned per policy

---

### Edge Cases

- What happens when Odoo credentials expire mid-operation?
- How does the system handle rate limits from social media platforms?
- What if the CEO Briefing runs but no accounting data is available?
- How are partial failures handled in multi-step Ralph Wiggum loops?
- What happens when two social media platforms have conflicting post requirements?

## Requirements *(mandatory)*

### Functional Requirements

#### Odoo Integration
- **FR-001**: System MUST connect to Odoo Community Edition (v19+) via JSON-RPC API
- **FR-002**: System MUST authenticate with Odoo using database name, username, and API key
- **FR-003**: System MUST read invoices, payments, and account transactions from Odoo
- **FR-004**: System MUST create draft invoices in Odoo (requiring human approval before sending)
- **FR-005**: System MUST sync accounting data to vault's Accounting folder at configurable intervals

#### Social Media Integration
- **FR-006**: System MUST support Facebook Page posting via Graph API or browser automation
- **FR-007**: System MUST support Instagram posting via Graph API or browser automation
- **FR-008**: System MUST support Twitter/X posting via API v2 or browser automation
- **FR-009**: System MUST validate post content against platform-specific limits before submission
- **FR-010**: All social media posts MUST require human approval before publishing
- **FR-011**: System MUST retrieve and log engagement metrics after posting

#### CEO Briefing
- **FR-012**: System MUST generate weekly briefings on a configurable schedule (default: Sunday 11 PM)
- **FR-013**: Briefing MUST include: revenue summary, expense summary, completed tasks, bottlenecks, proactive suggestions
- **FR-014**: System MUST read from Business_Goals.md to compare actual vs. target metrics
- **FR-015**: Briefing MUST identify tasks that exceeded expected duration as bottlenecks
- **FR-016**: System MUST suggest cost optimizations based on subscription/expense patterns

#### Ralph Wiggum Loop
- **FR-017**: System MUST implement Stop hook pattern to keep Claude iterating until task completion
- **FR-018**: Loop MUST support promise-based completion (`<promise>TASK_COMPLETE</promise>`)
- **FR-019**: Loop MUST support file-movement completion (task moved to Done folder)
- **FR-020**: Loop MUST respect max_iterations limit (default: 10) to prevent infinite loops
- **FR-021**: Loop MUST have per-iteration timeout (default: 300 seconds)

#### MCP Servers
- **FR-022**: System MUST support multiple MCP servers running concurrently
- **FR-023**: Each MCP server MUST have independent circuit breaker and rate limiter
- **FR-024**: Required MCP servers: email, odoo-accounting, social-media (Facebook/Instagram/Twitter)
- **FR-025**: MCP servers MUST expose health check endpoints

#### Error Recovery
- **FR-026**: System MUST implement exponential backoff retry for transient failures
- **FR-027**: System MUST use circuit breakers to prevent cascading failures
- **FR-028**: System MUST gracefully degrade when non-critical components fail
- **FR-029**: System MUST queue failed actions for retry when services recover

#### Audit Logging
- **FR-030**: All actions MUST be logged to daily JSON files in Logs folder
- **FR-031**: Log entries MUST include: timestamp, action_type, component, actor, target, parameters, approval_status, result
- **FR-032**: Logs MUST be retained for minimum 90 days

#### Agent Skills
- **FR-033**: All new AI functionality MUST be implemented as Agent Skills
- **FR-034**: Skills MUST follow the existing skill template structure
- **FR-035**: Skills MUST include documentation of capabilities and usage

### Key Entities

- **OdooConnection**: Represents connection to Odoo instance (database, user, credentials, base URL)
- **Invoice**: Financial document (number, customer, line items, amounts, status, due date)
- **Transaction**: Accounting entry (date, type, amount, category, reference)
- **SocialPost**: Content to be published (platform, content, media, scheduled_time, status, engagement_metrics)
- **CEOBriefing**: Weekly report (period, revenue, expenses, tasks_completed, bottlenecks, suggestions)
- **LoopState**: Ralph Wiggum execution state (loop_id, prompt, iterations, status, output_history)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Business owner can view weekly financial summary without logging into Odoo directly
- **SC-002**: CEO Briefing is generated within 10 minutes of scheduled time with 99% reliability
- **SC-003**: Social media posts are published within 5 minutes of approval
- **SC-004**: 95% of multi-step tasks complete successfully via Ralph Wiggum loop without human intervention
- **SC-005**: System recovers from transient failures within 3 retry attempts
- **SC-006**: All actions are traceable via audit logs within 24 hours of occurrence
- **SC-007**: System handles 50+ accounting transactions per day without performance degradation
- **SC-008**: Social media engagement metrics are retrieved within 1 hour of posting

## Assumptions

- Odoo Community Edition v19+ is installed and accessible via network
- Social media accounts have appropriate API access or browser sessions configured
- Existing Silver Tier infrastructure (watchers, HITL, orchestrator) is functional
- Company Handbook rules define which actions require approval
- Business owner has documented Business_Goals.md with targets and metrics

## Out of Scope

- Odoo Enterprise-specific features
- Social media advertising/paid campaigns
- Real-time social media monitoring (polling-based only)
- Multi-user access control (single owner assumed)
- Mobile app integration
- Video content posting (images and text only for this tier)

## Dependencies

- Silver Tier must be complete (watchers, HITL, orchestrator, email MCP)
- Odoo instance must be accessible
- Social media credentials/sessions must be configured
- Playwright installed for browser-based automation fallbacks
