# Personal AI Employee - Digital FTE System

> **Last Updated:** 2026-02-06
> **Current Branch:** `main`
> **Status:** Bronze complete, Gold & Platinum implemented

---

## What Is This Project?

**Personal AI Employee** is an autonomous Digital FTE (Full-Time Equivalent) — an AI agent that manages your personal and business affairs 24/7 using **Claude Code** as the brain and **Obsidian** as the memory/dashboard.

Think of it as hiring a senior employee who:
- **Watches** for inputs (emails, files dropped, WhatsApp messages, LinkedIn)
- **Reasons** using Claude Code (reads context, analyzes, creates plans)
- **Acts** via MCP servers (sends emails, posts on social media, creates invoices)
- **Remembers** everything in a local Obsidian vault (markdown files)
- **Asks for permission** before doing anything sensitive (Human-in-the-Loop)

### Core Architecture: Perception → Reasoning → Action → Memory

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   WATCHERS  │───>│   OBSIDIAN  │<───│ CLAUDE CODE │
│  (Sensors)  │    │   (Memory)  │    │   (Brain)   │
└─────────────┘    └─────────────┘    └──────┬──────┘
       │                                      │
       │           ┌─────────────┐           │
       └──────────>│     MCP     │<──────────┘
                   │   (Hands)   │
                   └─────────────┘
```

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| **Perception** | Watchers (Python scripts) | Monitor inputs, create `.md` action files in `/Needs_Action/` |
| **Reasoning** | Claude Code | Read vault, analyze, plan, decide, write plans |
| **Action** | MCP Servers | Execute approved actions (send email, post, pay) |
| **Memory** | Obsidian Vault | All state stored as local markdown files |
| **Safety** | HITL (Human-in-the-Loop) | Human approves sensitive actions before execution |

---

## Development Tiers (Detailed)

The project is built in 4 progressive tiers. Each tier builds on top of the previous one.

### Bronze Tier: Foundation (Minimum Viable) — Status: COMPLETE

**Purpose:** Prove the core loop works — a watcher detects something, creates a file in the vault, and Claude Code can read and process it.

**What It Includes:**
1. **Obsidian Vault** (`AI_Employee_Vault/`) with the folder structure:
   - `Inbox/` — Raw incoming items
   - `Needs_Action/` — Files that watchers create for Claude to process
   - `Plans/` — Claude's reasoning output
   - `Done/` — Completed items
   - `Logs/` — JSON audit logs
   - `Drop/` — Folder where you drop files to trigger the watcher
   - `Dashboard.md` — Real-time status overview
   - `Company_Handbook.md` — Rules the AI follows
   - `Business_Goals.md` — Strategic objectives
2. **FileSystem Watcher** (`src/watchers/filesystem_watcher.py`):
   - Uses Python `watchdog` library to monitor the `Drop/` folder
   - When you drop a file into `Drop/`, it automatically creates a metadata `.md` file in `Needs_Action/`
3. **Claude Code Integration:**
   - Claude Code reads from the vault (reads `Needs_Action/`, `Company_Handbook.md`, etc.)
   - Claude Code writes back to the vault (creates plans in `Plans/`, moves items to `Done/`)
   - The `/process-inbox` skill tells Claude to process everything in `Needs_Action/`
4. **Base Watcher Class** (`src/watchers/base_watcher.py`):
   - Abstract base class that all watchers extend
   - Provides `check_for_updates()` and `create_action_file()` pattern

**How to Test Bronze Tier:**
```bash
# 1. Install dependencies
cd Digital-Employees
uv venv
.venv\Scripts\activate   # Windows
uv pip install -r requirements.txt

# 2. Start the filesystem watcher
python -m src.watchers.filesystem_watcher --vault ./AI_Employee_Vault

# 3. In another terminal, drop a test file
copy any_file.txt AI_Employee_Vault\Drop\

# 4. Check that an action file appeared
dir AI_Employee_Vault\Needs_Action\
# You should see a new FILE_*.md file

# 5. Use Claude Code to process it
# Open Claude Code in this directory and run:
/process-inbox
# Claude will read Needs_Action/, reason about items, and move them to Done/
```

**Bronze Tier is working if:**
- Dropping a file into `Drop/` creates a `.md` file in `Needs_Action/`
- Claude Code can read the vault and process items
- Processed items end up in `Done/` or `Plans/`
- Logs are written to `Logs/`

---

### Silver Tier: Functional Assistant — Status: PLANNED

**Purpose:** Add real-world input sources (email, WhatsApp, LinkedIn), enable Claude to take actions via MCP servers, and add human approval for sensitive actions.

**What It Adds on Top of Bronze:**
1. **Gmail Watcher** (`src/watchers/gmail_watcher.py`):
   - Monitors Gmail via Google API for unread/important emails
   - Creates `EMAIL_*.md` files in `Needs_Action/` with sender, subject, body
2. **WhatsApp Watcher** (`src/watchers/whatsapp_watcher.py`):
   - Uses Playwright to automate WhatsApp Web
   - Monitors for messages matching keywords ("urgent", "invoice", "payment", "help")
   - Creates `WHATSAPP_*.md` files in `Needs_Action/`
3. **LinkedIn Watcher** (`src/watchers/linkedin_watcher.py`):
   - Monitors LinkedIn for connection requests and messages
   - Auto-posts business content to generate leads
4. **MCP Servers** (Action execution):
   - Email MCP — Send emails via Gmail API
   - At least one working MCP server for external actions
5. **Human-in-the-Loop (HITL)** (`src/utils/hitl.py`):
   - Sensitive actions create approval files in `Pending_Approval/`
   - Human reviews in Obsidian, moves to `Approved/` or `Rejected/`
   - Only approved actions get executed by MCP
6. **Basic Scheduling** via cron (Linux/Mac) or Task Scheduler (Windows)

**How the HITL Flow Works:**
```
Watcher detects item → Needs_Action/
  → Claude analyzes → Creates Plan in Plans/
  → If approval needed → Pending_Approval/
  → Human reviews in Obsidian:
      Approve → moves file to Approved/
      Reject  → moves file to Rejected/
  → MCP executes approved actions → Done/
```

---

### Gold Tier: Autonomous Employee — Status: IMPLEMENTED

**Purpose:** Full cross-domain integration covering business accounting, social media across all platforms, autonomous multi-step task completion, and weekly CEO briefings.

**What It Adds on Top of Silver:**
1. **Odoo Accounting Integration** (`src/lib/odoo_client.py`, `src/mcp_servers/odoo_mcp.py`):
   - Connects to Odoo Community (self-hosted ERP) via JSON-RPC API
   - Watcher monitors invoices, payments, overdue items
   - MCP can create invoices, record payments (with approval)
2. **Social Media Integration** (`src/lib/social_clients/`, `src/mcp_servers/social_mcp.py`):
   - Facebook, Instagram, Twitter/X posting
   - Content scheduling and engagement summaries
3. **CEO Briefing** (`src/skills/ceo_briefing.py`):
   - Weekly autonomous business audit
   - Reads `Business_Goals.md`, checks `Done/` folder, reviews accounting data
   - Generates Monday Morning CEO Briefing in `Briefings/` with:
     - Revenue summary
     - Task completion bottlenecks
     - Proactive suggestions ("You're paying for Notion but nobody logged in for 45 days")
4. **Ralph Wiggum Loop** (`src/utils/ralph_wiggum.py`):
   - Multi-step autonomous reasoning — Claude keeps working until task is done
   - Stop hook pattern: Claude tries to exit → hook checks if task file is in `/Done/` → if not, re-injects prompt → Claude continues
   - Prevents the "lazy agent" problem where Claude stops after one step
5. **Comprehensive Audit Logging** (`src/utils/audit_logger.py`):
   - Every action logged as JSON with timestamp, actor, result
   - Daily log files in `Logs/YYYY-MM-DD.json`
6. **Error Recovery & Graceful Degradation**:
   - If one watcher crashes, others continue
   - Exponential backoff for transient failures
   - Never auto-retry failed payments

---

### Platinum Tier: Always-On Cloud + Local — Status: IMPLEMENTED

**Purpose:** Run the AI Employee 24/7 on a cloud VM while keeping sensitive operations on the local machine. Two agents (Cloud + Local) split work by domain.

**What It Adds on Top of Gold:**
1. **Cloud VM Deployment** (Oracle Cloud Free Tier / AWS):
   - Always-on watchers + orchestrator + health monitoring
   - PM2 process management for auto-restart
   - HTTPS for all external communications
2. **Work-Zone Specialization (Two Agents):**
   - **Cloud Agent (24/7):** Email triage, draft replies, social post drafts, Odoo draft actions — NEVER sends/posts/pays, only drafts
   - **Local Agent (on-demand):** Approvals, WhatsApp, payments/banking, final send/post — has full execution access
3. **Vault Sync via Git:**
   - Cloud and Local share the vault through Git
   - < 30 second sync latency
   - **Claim-by-move rule:** First agent to move an item from `Needs_Action/` to `In_Progress/<agent>/` owns it
   - **Single-writer rule:** Only Local writes to `Dashboard.md`; Cloud writes to `Updates/` and Local merges
4. **Security Boundaries:**
   - Secrets (.env, tokens, WhatsApp sessions, banking creds) NEVER sync to cloud
   - Cloud only has access to markdown/state files
   - Cloud can never execute payments or send messages
5. **Odoo on Cloud VM:**
   - Odoo Community deployed with HTTPS, backups, health monitoring
   - Cloud agent does draft-only accounting actions
   - Local agent approves and posts invoices/payments
6. **Health Monitoring** (`AI_Employee_Vault/Health/status.md`):
   - Cloud agent health checks, process status, API connectivity, resource usage

**Platinum Demo (Minimum Passing Gate):**
```
1. Email arrives while your laptop (Local) is offline
2. Cloud agent drafts a reply + creates approval file
3. You open your laptop → Local syncs vault via Git
4. You review and approve in Obsidian
5. Local agent executes send via Email MCP
6. Logs transaction, moves task to Done/
```

---

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Core language for watchers, orchestrator |
| Claude Code | Latest | AI reasoning engine (the "brain") |
| Obsidian | v1.10.6+ | Local markdown vault (memory + dashboard) |
| Watchdog | >=4.0.0 | File system monitoring (Bronze) |
| Pydantic | >=2.5.0 | Data validation for models |
| Playwright | >=1.40.0 | WhatsApp/LinkedIn web automation (Silver) |
| google-api-python-client | >=2.100.0 | Gmail API (Silver) |
| Odoo JSON-RPC | Odoo 19+ | Accounting integration (Gold) |
| PM2 | Latest | Process management on cloud (Platinum) |
| Git | Latest | Vault sync between Cloud and Local (Platinum) |

### Development Tools
| Tool | Purpose |
|------|---------|
| UV | Python package manager (recommended) |
| pytest | Testing |
| Black | Code formatting |
| Ruff | Linting |
| mypy | Type checking |

---

## Project Structure

```
Digital-Employees/
├── AI_Employee_Vault/           # Obsidian Vault (Memory + Dashboard)
│   ├── Inbox/                   # Raw incoming items
│   ├── Needs_Action/            # Watcher outputs → Claude processes these
│   ├── Plans/                   # Claude's reasoning/plan outputs
│   ├── Pending_Approval/        # Actions waiting for human approval
│   ├── Approved/                # Human-approved actions → MCP executes
│   ├── Rejected/                # Human-rejected actions
│   ├── Done/                    # Completed items (audit trail)
│   ├── Logs/                    # JSON audit logs (daily: YYYY-MM-DD.json)
│   ├── Drop/                    # Drop files here → triggers FileSystem Watcher
│   ├── Accounting/              # Financial data (Gold tier)
│   ├── Social/                  # Social media posts (Gold tier)
│   ├── Briefings/               # CEO briefings (Gold tier)
│   ├── Health/                  # Agent health status (Platinum tier)
│   ├── Company_Handbook.md      # Rules the AI follows (thresholds, limits)
│   ├── Business_Goals.md        # Strategic objectives and KPIs
│   └── Dashboard.md             # Real-time system status
│
├── src/
│   ├── watchers/                # Perception Layer (detect inputs)
│   │   ├── base_watcher.py      # Abstract base class for all watchers
│   │   ├── filesystem_watcher.py # Monitors Drop/ folder (Bronze)
│   │   ├── gmail_watcher.py     # Monitors Gmail (Silver)
│   │   ├── whatsapp_watcher.py  # Monitors WhatsApp (Silver)
│   │   ├── linkedin_watcher.py  # Monitors LinkedIn (Silver)
│   │   └── odoo_watcher.py      # Monitors Odoo accounting (Gold)
│   │
│   ├── lib/                     # Library/API Clients
│   │   ├── odoo_client.py       # Odoo JSON-RPC integration (Gold)
│   │   └── social_clients/      # Social media API clients (Gold)
│   │
│   ├── mcp_servers/             # Action Layer (execute approved actions)
│   │   ├── email_mcp.py         # Send emails (Silver)
│   │   ├── odoo_mcp.py          # Create invoices, record payments (Gold)
│   │   └── social_mcp.py        # Post to social media (Gold)
│   │
│   ├── models/                  # Pydantic Data Models
│   │   ├── loop_state.py        # Ralph Wiggum loop state (Gold)
│   │   └── invoice.py           # Invoice model (Gold)
│   │
│   ├── skills/                  # Reasoning Skills (Claude Code skills)
│   │   ├── process_inbox.py     # Process Needs_Action/ items
│   │   └── ceo_briefing.py      # Generate CEO briefings (Gold)
│   │
│   └── utils/                   # Shared Utilities
│       ├── ralph_wiggum.py      # Multi-step reasoning loop (Gold)
│       ├── hitl.py              # Human-in-the-loop approval (Silver)
│       └── audit_logger.py      # Audit logging (Gold)
│
├── .claude/                     # Claude Code Configuration
│   ├── commands/                # Slash commands (e.g., /process-inbox)
│   ├── agents/                  # Claude Code agents
│   └── skills/                  # Skills (gmail-watcher, whatsapp-watcher, etc.)
│
├── specs/                       # Feature Specifications
│   ├── 001-gold-tier/           # Gold tier spec, plan, tasks
│   └── 002-platinum-tier/       # Platinum tier spec, plan, tasks
│
├── .specify/                    # Spec-Driven Development Framework
│   ├── memory/constitution.md   # Project constitution (principles)
│   └── templates/               # SDD templates
│
├── history/                     # Project History
│   ├── prompts/                 # Prompt History Records (PHR)
│   └── adr/                     # Architecture Decision Records
│
├── tests/                       # Test Suite
├── orchestrator.py              # Main entry point (spawns watchers)
├── pyproject.toml               # Project metadata
├── requirements.txt             # Python dependencies
├── requirements.md.md           # Full hackathon requirements document
└── .env.example                 # Environment variable template
```

---

## How to Run the Project

### Prerequisites
- Python 3.11+ (3.13 recommended)
- Node.js 20+ (for Claude Code)
- Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
- Obsidian (optional, for viewing the vault as a dashboard)
- UV (recommended Python package manager)

### Setup
```bash
# 1. Clone and enter the project
cd Digital-Employees

# 2. Create virtual environment
uv venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Install dependencies
uv pip install -r requirements.txt
# Or with pip:
pip install -r requirements.txt

# 4. Copy and edit environment config
cp .env.example .env
# Edit .env with your credentials
```

### Running Bronze Tier (File Watcher + Claude)
```bash
# Terminal 1: Start the filesystem watcher
python -m src.watchers.filesystem_watcher --vault ./AI_Employee_Vault

# Terminal 2: Drop a file to test
copy myfile.txt AI_Employee_Vault\Drop\     # Windows
cp myfile.txt AI_Employee_Vault/Drop/       # Linux/Mac

# Check Needs_Action/ for the generated action file
# Then in Claude Code:
/process-inbox
```

### Running Full Orchestrator (All Watchers)
```bash
python orchestrator.py
```

---

## Configuration

### Environment Variables (.env)
```bash
# Core (Bronze)
DRY_RUN=true                    # Set to false for real actions
VAULT_PATH=./AI_Employee_Vault

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

# Cloud (Platinum)
# See specs/002-platinum-tier/spec.md for cloud config
```

### Key Rules (Company_Handbook.md)
- **Auto-approve:** <$50 recurring to known vendors
- **Always require approval:** >$100, new recipients, international transfers
- **Never auto-approve:** crypto, wire transfers, personal accounts
- **Rate limits:** 10 emails/hour, 3 payments/hour, 5 social posts/day
- **Escalate immediately:** >$500, legal docs, security concerns

---

## Core Principles

1. **Local-First Privacy** — All data stored locally in the Obsidian vault; minimal cloud exposure
2. **Human-in-the-Loop (NON-NEGOTIABLE)** — Sensitive actions require explicit human approval
3. **Audit Everything** — Every action logged with ISO 8601 timestamp in JSON
4. **Graceful Degradation** — If one watcher fails, others continue; system never fully crashes
5. **Separation of Concerns** — Watchers detect, Claude reasons, MCP acts, Vault remembers
6. **Defensive Defaults** — DRY_RUN=true, approval required by default, rate limits enforced
7. **No Hardcoded Secrets** — All credentials via `.env` only, never in vault or version control

---

## Related Documentation

- **Full Requirements:** `requirements.md.md` (hackathon blueprint with all details)
- **Constitution:** `.specify/memory/constitution.md` (project principles)
- **Gold Tier Spec:** `specs/001-gold-tier/spec.md`
- **Platinum Tier Spec:** `specs/002-platinum-tier/spec.md`
- **Architecture Decisions:** `history/adr/`
- **Company Rules:** `AI_Employee_Vault/Company_Handbook.md`
- **Business Goals:** `AI_Employee_Vault/Business_Goals.md`

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
