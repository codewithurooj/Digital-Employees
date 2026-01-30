# Platinum Tier Specification: Always-On Cloud + Local Executive

**Version:** 1.0.0
**Date:** 2026-01-25
**Status:** Draft
**Estimated Effort:** 60+ hours
**Prerequisites:** Gold Tier completion

---

## 1. Problem Statement

The Gold Tier AI Employee operates effectively but requires the local machine to be running for continuous operation. Business opportunities are missed when the laptop is closed, and critical tasks wait until the user returns. The Platinum Tier transforms the AI Employee into a production-grade system with 24/7 cloud availability while maintaining security through a Cloud/Local split architecture where sensitive operations remain under local control.

---

## 2. User Personas

### 2.1 Business Owner (Primary)
- Needs 24/7 business monitoring even when away from computer
- Wants draft responses prepared for approval upon return
- Requires absolute control over payments and sensitive actions
- Expects seamless handoff between cloud and local agents

### 2.2 Remote Worker
- Works across multiple time zones
- Needs email triage happening while asleep
- Wants social media drafts ready for morning review
- Requires mobile-friendly approval workflow

### 2.3 Enterprise IT Administrator
- Manages cloud infrastructure deployment
- Monitors system health and uptime
- Handles security compliance and audit requirements
- Configures backup and disaster recovery

---

## 3. Success Criteria

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Cloud Uptime | 99.5% | Health monitoring dashboard |
| Draft Response Time | < 5 minutes | Timestamp comparison |
| Vault Sync Latency | < 30 seconds | Git push/pull timestamps |
| Local Approval to Action | < 60 seconds | Audit log timestamps |
| Secret Exposure | 0 incidents | Security audit |
| Data Loss | 0 events | Backup verification |

---

## 4. User Stories

### US-001: Cloud Email Triage
**As a** business owner
**I want** the cloud agent to triage my emails while I'm away
**So that** draft responses are ready when I return

**Acceptance Scenarios:**
```gherkin
Scenario: Email arrives while local is offline
  Given the local machine is offline
  And the cloud agent is running
  When an important email arrives in Gmail
  Then the cloud agent creates a draft response
  And writes an approval file to /Pending_Approval/email/
  And syncs the vault via Git

Scenario: Multiple emails prioritization
  Given 10 emails arrive within 1 hour
  When the cloud agent triages them
  Then emails are categorized by priority (urgent/normal/low)
  And urgent emails get draft responses first
  And a summary is written to /Updates/email_summary.md
```

### US-002: Cloud Social Media Scheduling
**As a** business owner
**I want** the cloud agent to draft and schedule social media posts
**So that** my online presence continues 24/7

**Acceptance Scenarios:**
```gherkin
Scenario: Social post draft creation
  Given a scheduled post time is approaching
  And the local machine is offline
  When the cloud agent prepares the post
  Then it creates a draft in /Pending_Approval/social/
  And does NOT publish without local approval

Scenario: Local approves social post
  Given the local machine comes online
  And there is a pending social post in /Pending_Approval/social/
  When the user moves the file to /Approved/social/
  Then the local agent publishes the post via MCP
  And logs the action to /Logs/
  And moves the file to /Done/
```

### US-003: Work-Zone Specialization
**As a** security-conscious user
**I want** clear boundaries between cloud and local capabilities
**So that** sensitive operations never execute without my presence

**Acceptance Scenarios:**
```gherkin
Scenario: Cloud attempts sensitive action
  Given the cloud agent detects a payment request
  When it processes the request
  Then it creates a draft only
  And writes to /Pending_Approval/payments/
  And does NOT execute the payment
  And logs "BLOCKED: payment requires local approval"

Scenario: Local exclusive actions
  Given an action requires WhatsApp, banking, or payment
  When the cloud agent encounters such a task
  Then it delegates to /Needs_Action/local/
  And waits for local processing
```

### US-004: Vault Synchronization
**As a** user with cloud and local agents
**I want** the vault to stay synchronized
**So that** both agents have current state information

**Acceptance Scenarios:**
```gherkin
Scenario: Cloud pushes updates
  Given the cloud agent completes a task
  When it writes to the vault
  Then it commits changes to Git
  And pushes to the remote repository
  Within 30 seconds of task completion

Scenario: Local pulls updates
  Given the local machine comes online
  When the orchestrator starts
  Then it pulls latest changes from Git
  And merges any /Updates/ files into Dashboard.md
  And processes any /Pending_Approval/ files

Scenario: Conflict prevention with claim-by-move
  Given a task exists in /Needs_Action/email/
  When both agents detect the task simultaneously
  Then only one agent successfully moves it to /In_Progress/<agent>/
  And the other agent ignores the task
```

### US-005: Cloud Odoo Integration
**As a** business owner
**I want** the cloud agent to interact with Odoo for accounting
**So that** financial operations continue 24/7 with appropriate controls

**Acceptance Scenarios:**
```gherkin
Scenario: Cloud creates draft invoice
  Given a client requests an invoice
  And the cloud agent receives the request
  When it processes the request
  Then it creates a draft invoice in Odoo (not posted)
  And writes approval request to /Pending_Approval/accounting/
  And the invoice remains in draft state until local approves

Scenario: Local posts invoice
  Given a draft invoice exists in Odoo
  And an approval file exists in /Approved/accounting/
  When the local agent processes the approval
  Then it posts the invoice in Odoo via JSON-RPC
  And sends the invoice to the customer
  And logs the complete transaction
```

### US-006: Health Monitoring
**As an** IT administrator
**I want** comprehensive health monitoring for the cloud agent
**So that** I'm alerted to issues before they impact operations

**Acceptance Scenarios:**
```gherkin
Scenario: Process health check
  Given the cloud orchestrator is running
  When the watchdog performs a health check
  Then it verifies all watcher processes are running
  And checks API connectivity (Gmail, Odoo)
  And reports status to /Health/status.md

Scenario: Auto-recovery on failure
  Given a watcher process crashes
  When the watchdog detects the failure
  Then it restarts the process within 60 seconds
  And logs the incident to /Logs/health/
  And sends an alert notification
```

### US-007: Platinum Demo Flow
**As a** hackathon judge
**I want** to see the complete Cloud/Local handoff
**So that** I can verify the system works as designed

**Acceptance Scenarios:**
```gherkin
Scenario: Complete platinum demo
  Given the local machine is offline
  And the cloud agent is running
  When an important email arrives
  Then the cloud agent drafts a reply
  And writes approval file to /Pending_Approval/email/
  And syncs via Git
  When the local machine comes online
  And the user approves the draft
  Then the local agent sends the email via MCP
  And logs the complete transaction
  And moves the task to /Done/
```

---

## 5. Functional Requirements

### 5.1 Cloud Infrastructure

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-CI-001 | Deploy Cloud VM on Oracle Cloud Free Tier, AWS, or equivalent | Must Have |
| FR-CI-002 | Configure VM with Python 3.13+, Node.js v24+, and PM2 | Must Have |
| FR-CI-003 | Install and configure always-on watchers (Gmail, file system) | Must Have |
| FR-CI-004 | Deploy orchestrator with automatic startup on boot | Must Have |
| FR-CI-005 | Implement health monitoring with auto-restart capabilities | Must Have |
| FR-CI-006 | Configure HTTPS for all external communications | Must Have |
| FR-CI-007 | Set up automated backups with 7-day retention | Should Have |
| FR-CI-008 | Implement resource monitoring (CPU, memory, disk) | Should Have |

### 5.2 Work-Zone Specialization

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-WZ-001 | Cloud agent handles email triage and draft responses | Must Have |
| FR-WZ-002 | Cloud agent creates social media post drafts only | Must Have |
| FR-WZ-003 | Cloud agent creates Odoo draft documents only (never posts) | Must Have |
| FR-WZ-004 | Local agent handles all approvals | Must Have |
| FR-WZ-005 | Local agent maintains WhatsApp session exclusively | Must Have |
| FR-WZ-006 | Local agent executes all payment/banking operations | Must Have |
| FR-WZ-007 | Local agent performs final send/post actions | Must Have |
| FR-WZ-008 | Clear domain boundaries documented in Company_Handbook.md | Must Have |

### 5.3 Vault Synchronization

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-VS-001 | Implement Git-based vault synchronization | Must Have |
| FR-VS-002 | Cloud agent commits and pushes after each task completion | Must Have |
| FR-VS-003 | Local agent pulls on startup and periodically (every 60s) | Must Have |
| FR-VS-004 | Implement claim-by-move rule for task ownership | Must Have |
| FR-VS-005 | Single-writer rule for Dashboard.md (Local only) | Must Have |
| FR-VS-006 | Cloud writes to /Updates/ folder; Local merges to Dashboard | Must Have |
| FR-VS-007 | Conflict detection and resolution strategy defined | Must Have |
| FR-VS-008 | Sync latency target: < 30 seconds | Should Have |

### 5.4 Security Architecture

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-SEC-001 | Secrets NEVER sync to cloud (.env, tokens, sessions) | Must Have |
| FR-SEC-002 | .gitignore explicitly excludes all credential files | Must Have |
| FR-SEC-003 | Cloud agent has read-only access to sensitive data references | Must Have |
| FR-SEC-004 | WhatsApp session files remain local only | Must Have |
| FR-SEC-005 | Banking credentials remain local only | Must Have |
| FR-SEC-006 | Payment tokens remain local only | Must Have |
| FR-SEC-007 | Vault sync includes only markdown and state files | Must Have |
| FR-SEC-008 | Audit log of all cloud actions for security review | Must Have |

### 5.5 Cloud Odoo Deployment

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-OD-001 | Deploy Odoo Community Edition on cloud VM | Must Have |
| FR-OD-002 | Configure HTTPS for Odoo access | Must Have |
| FR-OD-003 | Implement automated Odoo backups | Must Have |
| FR-OD-004 | Cloud MCP server for draft-only Odoo operations | Must Have |
| FR-OD-005 | Local approval required for posting invoices | Must Have |
| FR-OD-006 | Local approval required for posting payments | Must Have |
| FR-OD-007 | Health monitoring for Odoo service | Should Have |
| FR-OD-008 | Odoo database backup to separate storage | Should Have |

### 5.6 Folder Structure

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-FS-001 | /Needs_Action/<domain>/ for domain-specific tasks | Must Have |
| FR-FS-002 | /Plans/<domain>/ for domain-specific plans | Must Have |
| FR-FS-003 | /Pending_Approval/<domain>/ for approval workflows | Must Have |
| FR-FS-004 | /In_Progress/<agent>/ for claim-by-move ownership | Must Have |
| FR-FS-005 | /Updates/ for cloud-written updates | Must Have |
| FR-FS-006 | /Signals/ for inter-agent communication | Should Have |
| FR-FS-007 | /Health/ for health status files | Must Have |
| FR-FS-008 | Clear folder naming convention documented | Must Have |

### 5.7 Optional A2A Upgrade (Phase 2)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-A2A-001 | Design A2A message protocol for agent communication | Nice to Have |
| FR-A2A-002 | Replace selective file handoffs with A2A messages | Nice to Have |
| FR-A2A-003 | Maintain vault as audit record even with A2A | Nice to Have |
| FR-A2A-004 | Fallback to file-based communication on A2A failure | Nice to Have |

---

## 6. Non-Functional Requirements

### 6.1 Availability
- Cloud agent uptime: 99.5% (allows ~3.6 hours downtime/month)
- Automatic recovery within 60 seconds of process failure
- Graceful degradation when external APIs are unavailable

### 6.2 Performance
- Draft response creation: < 5 minutes from email receipt
- Vault sync latency: < 30 seconds
- Local approval to action execution: < 60 seconds
- Health check interval: 60 seconds

### 6.3 Security
- Zero secrets exposure to cloud environment
- All cloud communications over HTTPS
- Audit logging for all autonomous actions
- Credential rotation documented and tested

### 6.4 Scalability
- Support for multiple domain watchers
- Configurable resource limits per watcher
- Queue management for high-volume periods

### 6.5 Maintainability
- Centralized logging with 90-day retention
- Clear documentation for all deployment procedures
- Rollback procedures documented and tested
- Health dashboard accessible via local network

---

## 7. Technical Constraints

1. **Cloud Provider Limits**: Oracle Cloud Free Tier has resource limitations
2. **Git Sync Timing**: Network latency affects sync speed
3. **WhatsApp Session**: Cannot be shared; must remain on single local machine
4. **Odoo Resources**: Requires dedicated memory (~2GB minimum)
5. **PM2 Ecosystem**: Process management tied to PM2 tooling

---

## 8. Assumptions

1. User has Oracle Cloud, AWS, or equivalent account for VM deployment
2. Stable internet connection available for cloud VM (10+ Mbps)
3. Gold Tier implementation is complete and functional
4. User understands Git basics for vault synchronization
5. Local machine available at least once daily for approvals
6. User comfortable with basic Linux server administration

---

## 9. Dependencies

| Dependency | Type | Risk Level |
|------------|------|------------|
| Gold Tier Completion | Internal | High |
| Oracle Cloud Free Tier availability | External | Medium |
| Git remote repository (GitHub/GitLab) | External | Low |
| PM2 process manager | External | Low |
| Odoo Community Edition 19+ | External | Medium |
| Syncthing (alternative to Git) | External | Low |

---

## 10. Out of Scope

1. Mobile app for approvals (use vault sync instead)
2. Multi-user cloud deployment
3. Load balancing across multiple cloud VMs
4. Real-time video/audio processing
5. Custom Odoo module development
6. Kubernetes orchestration (use PM2 instead)

---

## 11. Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Cloud VM unavailable | Low | High | Configure health alerts; document failover |
| Git sync conflicts | Medium | Medium | Claim-by-move rule; conflict resolution docs |
| Secret exposure | Low | Critical | Strict .gitignore; security audit |
| Odoo backup failure | Medium | High | Multiple backup destinations; verify weekly |
| Cost overrun on cloud | Low | Medium | Monitor usage; set alerts at 80% quota |

---

## 12. Glossary

| Term | Definition |
|------|------------|
| Cloud Agent | AI Employee instance running on cloud VM |
| Local Agent | AI Employee instance running on user's machine |
| Work-Zone | Domain of responsibility (cloud vs local) |
| Claim-by-Move | First agent to move task to /In_Progress/ owns it |
| Draft-Only | Creating documents without posting/sending |
| Vault Sync | Git-based synchronization of Obsidian vault |
| A2A | Agent-to-Agent direct communication protocol |
| HITL | Human-in-the-Loop approval workflow |

---

## 13. Acceptance Checklist

- [ ] Cloud VM deployed and accessible via SSH
- [ ] Always-on watchers running with PM2
- [ ] Vault syncing via Git between cloud and local
- [ ] Work-zone specialization enforced
- [ ] Secrets never appear in synced vault
- [ ] Cloud Odoo deployed with HTTPS
- [ ] Health monitoring active with alerts
- [ ] Platinum demo flow passes end-to-end
- [ ] Documentation complete for deployment
- [ ] All AI functionality implemented as Agent Skills

---

## 14. References

- [Hackathon PDF](../Personal%20AI%20Employee%20Hackathon%200_%20Building%20Autonomous%20FTEs%20in%202026.pdf)
- [Gold Tier Specification](../001-gold-tier/spec.md)
- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)
- [PM2 Documentation](https://pm2.keymetrics.io/docs/)
- [Odoo External API](https://www.odoo.com/documentation/19.0/developer/reference/external_api.html)
