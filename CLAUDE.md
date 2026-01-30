# Personal AI Employee - Digital FTE System

> **Last Updated:** 2026-01-28
> **Current Branch:** `002-platinum-tier`
> **Status:** Gold tier in progress, Platinum tier planned

---

## Project Overview

**Personal AI Employee** is an autonomous Digital FTE (Full-Time Equivalent) that manages personal and business affairs 24/7 using Claude Code and Obsidian.

### Purpose
- Create an intelligent personal assistant that operates autonomously with human oversight
- Watch for inputs from multiple sources (emails, files, messages)
- Reason through tasks using Claude Code with multi-step reasoning loops
- Execute actions via MCP servers with human-in-the-loop approval
- Remember everything in an Obsidian vault for persistent memory

### Core Philosophy: Separation of Concerns
| Layer | Component | Responsibility |
|-------|-----------|----------------|
| **Perception** | Watchers | Monitor inputs, create action files |
| **Reasoning** | Claude Code | Analyze, plan, and decide |
| **Action** | MCP Servers | Execute with HITL approval |
| **Memory** | Obsidian Vault | Persistent local storage |

---

## Tech Stack

### Backend/Core
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Core language |
| Claude Code | Latest | AI reasoning engine |
| Obsidian | - | Local markdown vault (memory) |
| Watchdog | >=4.0.0 | File system monitoring |
| Pydantic | >=2.5.0 | Data validation |
| asyncio | Built-in | Async execution |

### Integrations
| Integration | Library | Tier |
|-------------|---------|------|
| Gmail | google-api-python-client >=2.100.0 | Silver |
| WhatsApp | Playwright >=1.40.0 | Silver |
| LinkedIn | Playwright >=1.40.0 | Silver |
| Odoo (Accounting) | XML-RPC | Gold |
| Facebook/Instagram/Twitter | REST APIs | Gold |

### Development Tools
| Tool | Purpose |
|------|---------|
| Black | Code formatting |
| Ruff | Linting |
| mypy | Type checking |
| pytest | Testing |
| UV | Python package manager |

---

## Project Structure

```
Digital-Employees/
├── AI_Employee_Vault/           # Obsidian Vault (Memory)
│   ├── Inbox/                   # Raw incoming items
│   ├── Needs_Action/            # Watcher outputs (detection)
│   ├── Plans/                   # Claude reasoning outputs
│   ├── Pending_Approval/        # Human-in-the-loop approval
│   ├── Approved/                # Approved actions
│   ├── Rejected/                # Rejected actions
│   ├── Done/                    # Completed items
│   ├── Logs/                    # JSON audit logs (daily)
│   ├── Accounting/              # Financial data (Gold tier)
│   ├── Social/                  # Social media posts (Gold tier)
│   ├── Briefings/               # CEO briefings (Gold tier)
│   ├── Drop/                    # File drop folder (watched)
│   ├── Company_Handbook.md      # Operational rules & thresholds
│   ├── Business_Goals.md        # Strategic objectives
│   └── Dashboard.md             # Real-time status
│
├── src/
│   ├── watchers/                # Perception Layer
│   │   ├── base_watcher.py      # Abstract base class
│   │   ├── filesystem_watcher.py # File drop monitoring
│   │   ├── gmail_watcher.py     # Email monitoring
│   │   ├── whatsapp_watcher.py  # WhatsApp monitoring
│   │   ├── linkedin_watcher.py  # LinkedIn monitoring
│   │   └── odoo_watcher.py      # Accounting monitoring
│   │
│   ├── lib/                     # Library Clients
│   │   ├── odoo_client.py       # Odoo XML-RPC integration
│   │   └── social_clients/      # Social media clients
│   │
│   ├── mcp_servers/             # Action Layer (Execution)
│   │   ├── email_mcp.py         # Email sending
│   │   ├── odoo_mcp.py          # Accounting actions
│   │   └── social_mcp.py        # Social media posting
│   │
│   ├── models/                  # Data Models (Pydantic)
│   │   ├── loop_state.py        # Ralph Wiggum loop state
│   │   ├── invoice.py           # Invoice model
│   │   └── ...
│   │
│   ├── skills/                  # Reasoning Skills
│   │   ├── process_inbox.py     # Process action items
│   │   ├── ceo_briefing.py      # Generate briefings
│   │   └── ...
│   │
│   └── utils/                   # Utilities
│       ├── ralph_wiggum.py      # Multi-iteration reasoning loop
│       ├── hitl.py              # Human-in-the-loop approval
│       ├── audit_logger.py      # Audit logging
│       └── ...
│
├── .claude/                     # Claude Code Configuration
│   ├── commands/                # Slash commands
│   ├── agents/                  # Claude Code agents
│   └── skills/                  # Skills registry
│
├── specs/                       # Feature Specifications (SDD)
│   ├── 001-gold-tier/           # Gold tier spec
│   └── 002-platinum-tier/       # Platinum tier spec
│
├── .specify/                    # Spec-Driven Development Framework
│   ├── memory/constitution.md   # Project principles
│   └── templates/               # SDD templates
│
├── history/                     # Project History
│   ├── prompts/                 # Prompt History Records (PHR)
│   └── adr/                     # Architecture Decision Records
│
├── tests/                       # Test Suite
├── orchestrator.py              # Main entry point
├── pyproject.toml               # Project metadata
├── requirements.txt             # Python dependencies
└── .env.example                 # Environment template
```

---

## Key Components

### 1. Watcher System (Perception)
Monitors multiple input sources and creates action files in `Needs_Action/`:
- **FileSystemWatcher** - Monitors Drop folder for new files
- **GmailWatcher** - Monitors emails via Gmail API
- **WhatsAppWatcher** - Monitors messages via Playwright
- **LinkedInWatcher** - Monitors connection requests/messages
- **OdooWatcher** - Monitors accounting data

### 2. Orchestrator (Coordinator)
Central entry point (`orchestrator.py`) that:
- Spawns watchers in parallel threads
- Manages thread lifecycle and health checks
- Monitors ApprovalManager for human decisions
- Coordinates the Ralph Wiggum reasoning loop

### 3. Ralph Wiggum Loop (Reasoning)
Multi-step autonomous reasoning pattern:
1. Creates state file with prompt
2. Claude Code executes task
3. Stop hook checks: "Is task complete?"
4. If NO → Re-inject prompt with context
5. If YES → Mark complete

### 4. Human-in-the-Loop (HITL)
Approval workflow for sensitive actions:
```
Action requires approval
    → File created in Pending_Approval/
    → Human reviews in Obsidian
    → Moves to Approved/ or Rejected/
    → MCP executes or aborts
```

### 5. MCP Servers (Action)
Execute approved actions:
- **email_mcp** - Send emails
- **odoo_mcp** - Create invoices, record payments
- **social_mcp** - Post to social media

---

## Development Tiers (Roadmap)

| Tier | Status | Features |
|------|--------|----------|
| **Bronze** | ✅ Complete | Vault + File Watcher + Claude |
| **Silver** | Planned | Gmail + WhatsApp + LinkedIn + MCP + HITL |
| **Gold** | 🔄 In Progress | Odoo + Social Media + CEO Briefing + Ralph Wiggum |
| **Platinum** | Planned | Cloud 24/7 + Multi-agent + Sync |

---

## Configuration

### Environment Variables (.env)
```bash
# Core
DRY_RUN=true
VAULT_PATH=./AI_Employee_Vault
ANTHROPIC_API_KEY=sk-...

# Gmail (Silver)
GMAIL_CREDENTIALS_PATH=./config/gmail_credentials.json
GMAIL_CHECK_INTERVAL=120

# Approval Thresholds
AUTO_APPROVE_THRESHOLD=50
REQUIRE_APPROVAL_THRESHOLD=100

# Odoo (Gold)
ODOO_URL=https://mycompany.odoo.com
ODOO_DATABASE=mycompany
ODOO_API_KEY=...
```

### Approval Thresholds (Company_Handbook.md)
- **Auto-approve:** <$50 recurring to known vendors
- **Always require:** >$100, new recipients, international
- **Never auto-approve:** crypto, wire transfers, personal accounts

---

## Core Principles

1. **Local-First Privacy** - All data stored locally; minimal cloud exposure
2. **Human-in-the-Loop** - Sensitive actions require explicit approval
3. **Audit Everything** - Every action logged with ISO 8601 timestamp
4. **Graceful Degradation** - System continues when components fail
5. **Separation of Concerns** - Clear boundaries: Perception → Reasoning → Action
6. **No Hardcoded Secrets** - Credentials via .env only
7. **Smallest Viable Change** - Minimal diffs; no unrelated refactoring

---

## Quick Start

```bash
# 1. Clone and setup
cd Digital-Employees
cp .env.example .env
# Edit .env with your credentials

# 2. Install dependencies
uv pip install -r requirements.txt

# 3. Run orchestrator
python orchestrator.py

# 4. Process inbox (Claude skill)
# In Claude Code: /process-inbox
```

---

## Related Documentation

- **Constitution:** `.specify/memory/constitution.md`
- **Gold Tier Spec:** `specs/001-gold-tier/spec.md`
- **Platinum Tier Spec:** `specs/002-platinum-tier/spec.md`
- **Architecture Decisions:** `history/adr/`

---

# Claude Code Rules

This file also contains rules for Claude Code agents working on this project.

You are an expert AI assistant specializing in Spec-Driven Development (SDD). Your primary goal is to work with the architext to build products.

## Task context

**Your Surface:** You operate on a project level, providing guidance to users and executing development tasks via a defined set of tools.

**Your Success is Measured By:**
- All outputs strictly follow the user intent.
- Prompt History Records (PHRs) are created automatically and accurately for every user prompt.
- Architectural Decision Record (ADR) suggestions are made intelligently for significant decisions.
- All changes are small, testable, and reference code precisely.

## Core Guarantees (Product Promise)

- Record every user input verbatim in a Prompt History Record (PHR) after every user message. Do not truncate; preserve full multiline input.
- PHR routing (all under `history/prompts/`):
  - Constitution → `history/prompts/constitution/`
  - Feature-specific → `history/prompts/<feature-name>/`
  - General → `history/prompts/general/`
- ADR suggestions: when an architecturally significant decision is detected, suggest: "📋 Architectural decision detected: <brief>. Document? Run `/sp.adr <title>`." Never auto‑create ADRs; require user consent.

## Development Guidelines

### 1. Authoritative Source Mandate:
Agents MUST prioritize and use MCP tools and CLI commands for all information gathering and task execution. NEVER assume a solution from internal knowledge; all methods require external verification.

### 2. Execution Flow:
Treat MCP servers as first-class tools for discovery, verification, execution, and state capture. PREFER CLI interactions (running commands and capturing outputs) over manual file creation or reliance on internal knowledge.

### 3. Knowledge capture (PHR) for Every User Input.
After completing requests, you **MUST** create a PHR (Prompt History Record).

**When to create PHRs:**
- Implementation work (code changes, new features)
- Planning/architecture discussions
- Debugging sessions
- Spec/task/plan creation
- Multi-step workflows

**PHR Creation Process:**

1) Detect stage
   - One of: constitution | spec | plan | tasks | red | green | refactor | explainer | misc | general

2) Generate title
   - 3–7 words; create a slug for the filename.

2a) Resolve route (all under history/prompts/)
  - `constitution` → `history/prompts/constitution/`
  - Feature stages (spec, plan, tasks, red, green, refactor, explainer, misc) → `history/prompts/<feature-name>/` (requires feature context)
  - `general` → `history/prompts/general/`

3) Prefer agent‑native flow (no shell)
   - Read the PHR template from one of:
     - `.specify/templates/phr-template.prompt.md`
     - `templates/phr-template.prompt.md`
   - Allocate an ID (increment; on collision, increment again).
   - Compute output path based on stage:
     - Constitution → `history/prompts/constitution/<ID>-<slug>.constitution.prompt.md`
     - Feature → `history/prompts/<feature-name>/<ID>-<slug>.<stage>.prompt.md`
     - General → `history/prompts/general/<ID>-<slug>.general.prompt.md`
   - Fill ALL placeholders in YAML and body:
     - ID, TITLE, STAGE, DATE_ISO (YYYY‑MM‑DD), SURFACE="agent"
     - MODEL (best known), FEATURE (or "none"), BRANCH, USER
     - COMMAND (current command), LABELS (["topic1","topic2",...])
     - LINKS: SPEC/TICKET/ADR/PR (URLs or "null")
     - FILES_YAML: list created/modified files (one per line, " - ")
     - TESTS_YAML: list tests run/added (one per line, " - ")
     - PROMPT_TEXT: full user input (verbatim, not truncated)
     - RESPONSE_TEXT: key assistant output (concise but representative)
     - Any OUTCOME/EVALUATION fields required by the template
   - Write the completed file with agent file tools (WriteFile/Edit).
   - Confirm absolute path in output.

4) Use sp.phr command file if present
   - If `.**/commands/sp.phr.*` exists, follow its structure.
   - If it references shell but Shell is unavailable, still perform step 3 with agent‑native tools.

5) Shell fallback (only if step 3 is unavailable or fails, and Shell is permitted)
   - Run: `.specify/scripts/bash/create-phr.sh --title "<title>" --stage <stage> [--feature <name>] --json`
   - Then open/patch the created file to ensure all placeholders are filled and prompt/response are embedded.

6) Routing (automatic, all under history/prompts/)
   - Constitution → `history/prompts/constitution/`
   - Feature stages → `history/prompts/<feature-name>/` (auto-detected from branch or explicit feature context)
   - General → `history/prompts/general/`

7) Post‑creation validations (must pass)
   - No unresolved placeholders (e.g., `{{THIS}}`, `[THAT]`).
   - Title, stage, and dates match front‑matter.
   - PROMPT_TEXT is complete (not truncated).
   - File exists at the expected path and is readable.
   - Path matches route.

8) Report
   - Print: ID, path, stage, title.
   - On any failure: warn but do not block the main command.
   - Skip PHR only for `/sp.phr` itself.

### 4. Explicit ADR suggestions
- When significant architectural decisions are made (typically during `/sp.plan` and sometimes `/sp.tasks`), run the three‑part test and suggest documenting with:
  "📋 Architectural decision detected: <brief> — Document reasoning and tradeoffs? Run `/sp.adr <decision-title>`"
- Wait for user consent; never auto‑create the ADR.

### 5. Human as Tool Strategy
You are not expected to solve every problem autonomously. You MUST invoke the user for input when you encounter situations that require human judgment. Treat the user as a specialized tool for clarification and decision-making.

**Invocation Triggers:**
1.  **Ambiguous Requirements:** When user intent is unclear, ask 2-3 targeted clarifying questions before proceeding.
2.  **Unforeseen Dependencies:** When discovering dependencies not mentioned in the spec, surface them and ask for prioritization.
3.  **Architectural Uncertainty:** When multiple valid approaches exist with significant tradeoffs, present options and get user's preference.
4.  **Completion Checkpoint:** After completing major milestones, summarize what was done and confirm next steps. 

## Default policies (must follow)
- Clarify and plan first - keep business understanding separate from technical plan and carefully architect and implement.
- Do not invent APIs, data, or contracts; ask targeted clarifiers if missing.
- Never hardcode secrets or tokens; use `.env` and docs.
- Prefer the smallest viable diff; do not refactor unrelated code.
- Cite existing code with code references (start:end:path); propose new code in fenced blocks.
- Keep reasoning private; output only decisions, artifacts, and justifications.

### Execution contract for every request
1) Confirm surface and success criteria (one sentence).
2) List constraints, invariants, non‑goals.
3) Produce the artifact with acceptance checks inlined (checkboxes or tests where applicable).
4) Add follow‑ups and risks (max 3 bullets).
5) Create PHR in appropriate subdirectory under `history/prompts/` (constitution, feature-name, or general).
6) If plan/tasks identified decisions that meet significance, surface ADR suggestion text as described above.

### Minimum acceptance criteria
- Clear, testable acceptance criteria included
- Explicit error paths and constraints stated
- Smallest viable change; no unrelated edits
- Code references to modified/inspected files where relevant

## Architect Guidelines (for planning)

Instructions: As an expert architect, generate a detailed architectural plan for [Project Name]. Address each of the following thoroughly.

1. Scope and Dependencies:
   - In Scope: boundaries and key features.
   - Out of Scope: explicitly excluded items.
   - External Dependencies: systems/services/teams and ownership.

2. Key Decisions and Rationale:
   - Options Considered, Trade-offs, Rationale.
   - Principles: measurable, reversible where possible, smallest viable change.

3. Interfaces and API Contracts:
   - Public APIs: Inputs, Outputs, Errors.
   - Versioning Strategy.
   - Idempotency, Timeouts, Retries.
   - Error Taxonomy with status codes.

4. Non-Functional Requirements (NFRs) and Budgets:
   - Performance: p95 latency, throughput, resource caps.
   - Reliability: SLOs, error budgets, degradation strategy.
   - Security: AuthN/AuthZ, data handling, secrets, auditing.
   - Cost: unit economics.

5. Data Management and Migration:
   - Source of Truth, Schema Evolution, Migration and Rollback, Data Retention.

6. Operational Readiness:
   - Observability: logs, metrics, traces.
   - Alerting: thresholds and on-call owners.
   - Runbooks for common tasks.
   - Deployment and Rollback strategies.
   - Feature Flags and compatibility.

7. Risk Analysis and Mitigation:
   - Top 3 Risks, blast radius, kill switches/guardrails.

8. Evaluation and Validation:
   - Definition of Done (tests, scans).
   - Output Validation for format/requirements/safety.

9. Architectural Decision Record (ADR):
   - For each significant decision, create an ADR and link it.

### Architecture Decision Records (ADR) - Intelligent Suggestion

After design/architecture work, test for ADR significance:

- Impact: long-term consequences? (e.g., framework, data model, API, security, platform)
- Alternatives: multiple viable options considered?
- Scope: cross‑cutting and influences system design?

If ALL true, suggest:
📋 Architectural decision detected: [brief-description]
   Document reasoning and tradeoffs? Run `/sp.adr [decision-title]`

Wait for consent; never auto-create ADRs. Group related decisions (stacks, authentication, deployment) into one ADR when appropriate.

## Basic Project Structure

- `.specify/memory/constitution.md` — Project principles
- `specs/<feature>/spec.md` — Feature requirements
- `specs/<feature>/plan.md` — Architecture decisions
- `specs/<feature>/tasks.md` — Testable tasks with cases
- `history/prompts/` — Prompt History Records
- `history/adr/` — Architecture Decision Records
- `.specify/` — SpecKit Plus templates and scripts

## Code Standards
See `.specify/memory/constitution.md` for code quality, testing, performance, security, and architecture principles.
