<!--
SYNC IMPACT REPORT
==================
Version change: N/A → 1.0.0 (Initial ratification)

Modified principles: N/A (Initial creation)

Added sections:
  - Core Principles (7 principles)
  - Security & Privacy Requirements
  - Operational Standards
  - Governance

Removed sections: N/A

Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ Compatible (Constitution Check section exists)
  - .specify/templates/spec-template.md: ✅ Compatible (Requirements section aligns)
  - .specify/templates/tasks-template.md: ✅ Compatible (Phase structure supports principles)

Follow-up TODOs: None
-->

# Personal AI Employee Constitution

## Core Principles

### I. Local-First Privacy

All personal and business data MUST be stored locally in the Obsidian vault by default. External
cloud services are permitted ONLY for:
- API calls to Claude Code (reasoning)
- Explicitly approved external integrations (Gmail API, etc.)
- User-initiated cloud sync (Platinum tier only)

**Rationale**: The AI Employee handles sensitive personal data (banking, messages, business
information). Local-first architecture ensures data sovereignty and minimizes breach surface.

**Compliance Check**:
- No credentials stored in cloud-synced locations
- Vault sync excludes .env, tokens, and session files
- All external API calls logged in /Logs

### II. Human-in-the-Loop (NON-NEGOTIABLE)

All sensitive actions MUST require explicit human approval before execution. Sensitive actions
include:
- Financial transactions of any amount to new recipients
- Financial transactions > $100 to known recipients
- Sending communications to new contacts
- Posting to public social media
- Deleting or moving files outside the vault
- Any action marked as "requires_approval" in Company_Handbook.md

**Rationale**: Autonomous systems can make mistakes. HITL ensures human accountability and
prevents irreversible harm from AI errors or hallucinations.

**Compliance Check**:
- Approval files MUST exist in /Pending_Approval before action execution
- Orchestrator MUST verify file moved to /Approved before proceeding
- All approved actions logged with human attribution

### III. Audit Everything

Every action the AI Employee takes MUST be logged with:
- ISO 8601 timestamp
- Action type and parameters
- Actor (watcher name, orchestrator, claude_code)
- Approval status (if applicable)
- Result (success/failure/error message)

Logs MUST be retained for minimum 90 days in /Logs folder.

**Rationale**: Comprehensive audit trails enable debugging, compliance verification, and
accountability. Without logs, autonomous failures become undiagnosable.

**Compliance Check**:
- Every watcher implements log_action() method
- Every MCP action logged before and after execution
- Daily log files in JSON format at /Logs/YYYY-MM-DD.json

### IV. Graceful Degradation

The system MUST continue operating when components fail. Required behaviors:
- Watcher failure: Queue items locally, alert human, continue other watchers
- MCP server failure: Create approval request for manual action, do not block
- Claude Code unavailable: Watchers continue collecting, queue grows for later
- Network failure: Never retry payments; queue other actions with exponential backoff

**Rationale**: A personal assistant that crashes completely on partial failure provides negative
value. Degraded operation is better than no operation.

**Compliance Check**:
- All watchers wrapped in try/except with logging
- Watchdog process monitors and restarts failed components
- Circuit breaker pattern for external API calls

### V. Separation of Concerns

The system MUST maintain clear boundaries between:
- **Perception** (Watchers): Monitor inputs, create action files, never execute
- **Reasoning** (Claude Code): Read, analyze, plan, never directly call external APIs
- **Action** (MCP Servers): Execute approved actions, never make decisions
- **Memory** (Obsidian Vault): Store state, never process or execute

**Rationale**: Clear separation enables independent testing, debugging, and replacement of
components. Violations create tight coupling and unpredictable behaviors.

**Compliance Check**:
- Watchers write only to /Needs_Action and /Logs
- Claude Code writes to /Plans, /Pending_Approval, updates Dashboard
- MCP servers read from /Approved, write to /Done and /Logs

### VI. Agent Skills Architecture

All AI functionality MUST be implemented as Agent Skills (reusable, documented command
patterns). Skills MUST:
- Have a single, clear purpose
- Be independently testable
- Include usage documentation
- Follow the naming convention: skill-name.md in .claude/commands/

**Rationale**: Skills enable consistent behavior, easier debugging, and knowledge transfer.
Ad-hoc prompting leads to inconsistent and unreproducible results.

**Compliance Check**:
- Every recurring task has a corresponding skill file
- Skills reference Company_Handbook.md rules
- New functionality added as skills, not inline prompts

### VII. Defensive Defaults

The system MUST default to safe behaviors:
- DRY_RUN=true for all new deployments
- New watchers start in monitor-only mode (no action file creation) for 24 hours
- Payment actions default to require approval regardless of amount
- Unknown message senders flagged for human review
- Rate limits: max 10 emails/hour, max 3 payments/hour, max 5 social posts/day

**Rationale**: Autonomous systems should fail safe. Overly aggressive defaults risk financial
loss, reputation damage, or security breaches during misconfiguration.

**Compliance Check**:
- .env.example shows DRY_RUN=true
- Rate limit counters in orchestrator
- New integrations require explicit enablement in config

## Security & Privacy Requirements

### Credential Management

- All secrets stored in .env files (NEVER in vault or version control)
- .env added to .gitignore before first commit
- Credentials rotated monthly and after any suspected breach
- Separate credentials for development and production environments
- WhatsApp sessions, banking tokens NEVER synced to cloud (Platinum tier)

### Data Classification

| Classification | Examples | Storage | Sync |
|---------------|----------|---------|------|
| Public | Social posts, public docs | Vault | Allowed |
| Internal | Business plans, task lists | Vault | Allowed |
| Confidential | Client data, invoices | Vault | Local only |
| Restricted | Credentials, banking | .env | Never |

### Access Control

- Claude Code: Read/write vault, no direct external API access
- Watchers: Write to /Needs_Action, /Inbox, /Logs only
- MCP Servers: Read /Approved, write /Done, /Logs, execute external APIs
- Human: Full access, sole approver for /Pending_Approval

## Operational Standards

### Folder Structure (Immutable)

```
AI_Employee_Vault/
├── Inbox/              # Raw incoming items
├── Needs_Action/       # Watcher outputs awaiting processing
├── Plans/              # Claude reasoning outputs
├── Pending_Approval/   # Actions requiring human approval
├── Approved/           # Human-approved actions
├── Rejected/           # Human-rejected actions
├── Done/               # Completed items (audit trail)
├── Logs/               # JSON audit logs
├── Accounting/         # Financial records
├── Briefings/          # Generated reports
├── Dashboard.md        # Real-time status (single-writer: local agent)
├── Company_Handbook.md # Operational rules
└── Business_Goals.md   # Objectives and metrics
```

### File Naming Conventions

- Action files: `{TYPE}_{TIMESTAMP}_{IDENTIFIER}.md`
- Log files: `{YYYY-MM-DD}.json`
- Plan files: `PLAN_{TIMESTAMP}_{SUBJECT}.md`
- Approval files: `{ACTION_TYPE}_{IDENTIFIER}_{TIMESTAMP}.md`

### Health Monitoring

- Orchestrator health check: every 60 seconds
- Watcher heartbeat: logged every check_interval
- Failed process restart: max 5 attempts with exponential backoff
- Human alert: after 3 consecutive failures or max restarts exceeded

## Governance

### Constitution Authority

This Constitution supersedes all other practices, configurations, and ad-hoc decisions. Any
conflict between this document and implementation MUST be resolved in favor of the
Constitution or through formal amendment.

### Amendment Process

1. Propose amendment with rationale in writing
2. Document impact on existing components
3. Update version following semantic versioning:
   - MAJOR: Principle removal or incompatible redefinition
   - MINOR: New principle or materially expanded guidance
   - PATCH: Clarifications, wording, non-semantic changes
4. Update all dependent templates and documentation
5. Record amendment in Sync Impact Report

### Compliance Review

- All pull requests MUST verify Constitution compliance
- Weekly self-audit: Review /Logs for principle violations
- Monthly review: Verify all skills reference current principles
- Quarterly review: Full Constitution relevance assessment

### Runtime Guidance

For development guidance, operational procedures, and implementation details, refer to:
- `roadmap.md` - Complete build guide
- `Company_Handbook.md` - Operational rules
- `.claude/commands/` - Agent skills

**Version**: 1.0.0 | **Ratified**: 2026-01-19 | **Last Amended**: 2026-01-19
