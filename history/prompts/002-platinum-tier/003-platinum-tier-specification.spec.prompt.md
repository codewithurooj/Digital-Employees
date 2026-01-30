---
id: 003
title: Platinum Tier Specification
stage: spec
date: 2026-01-25
surface: agent
model: claude-opus-4-5-20251101
feature: 002-platinum-tier
branch: 002-platinum-tier
user: pc1
command: /sp.specify write specification for the platinum tier of the project
labels: ["platinum-tier", "specification", "cloud", "local-agent", "vault-sync", "odoo", "always-on"]
links:
  spec: specs/002-platinum-tier/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - specs/002-platinum-tier/spec.md
  - specs/002-platinum-tier/checklists/requirements.md
tests:
  - Requirements checklist validation (all 12 criteria passed)
---

## Prompt

/sp.specify write specification for the platinum tier of the project

## Response snapshot

Created comprehensive Platinum Tier specification based on hackathon PDF requirements. The spec covers:

1. **Cloud Infrastructure** - VM deployment on Oracle/AWS with PM2, HTTPS, automated backups
2. **Work-Zone Specialization**:
   - Cloud owns: Email triage, draft replies, social post drafts/scheduling
   - Local owns: Approvals, WhatsApp session, payments/banking, final send/post
3. **Vault Synchronization** - Git-based sync with claim-by-move rule, single-writer Dashboard.md
4. **Security Architecture** - Secrets never sync; vault includes only markdown/state
5. **Cloud Odoo Deployment** - 24/7 Odoo with draft-only cloud operations
6. **Health Monitoring** - Watchdog, auto-restart, alerting
7. **Optional A2A Upgrade** - Phase 2 replacement of file handoffs with direct messages

Spec includes 7 user stories with Gherkin acceptance scenarios and 48 functional requirements across 7 categories.

**Platinum Demo (Minimum Passing Gate):**
Email arrives while Local offline -> Cloud drafts reply + approval file -> Local returns, user approves -> Local sends via MCP -> logs -> moves to /Done

## Outcome

- Impact: Created production-grade specification for always-on Cloud + Local Executive architecture
- Tests: Requirements checklist validation passed all 12 criteria
- Files: 2 files created (spec.md, requirements.md checklist)
- Next prompts: /sp.clarify or /sp.plan to continue workflow
- Reflection: Successfully translated hackathon PDF Platinum tier requirements into comprehensive spec with clear Cloud/Local boundaries

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): Requirements checklist PASS (12/12)
- Prompt variant (if applicable): null
- Next experiment (smallest change to try): Run /sp.clarify to validate Cloud/Local boundary definitions
