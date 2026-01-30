# Personal AI Employee

> An autonomous Digital FTE (Full-Time Equivalent) that manages personal and business affairs 24/7 using Claude Code + Obsidian.

## Overview

This system creates a personal AI assistant that:
- **Watches** for inputs (emails, files, messages)
- **Reasons** using Claude Code (analyzes, plans, decides)
- **Acts** via MCP servers (sends responses, manages tasks)
- **Remembers** everything in an Obsidian vault

```
┌─────────────────────────────────────────────────────────────────┐
│                    PERSONAL AI EMPLOYEE                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   WATCHERS  │───>│   OBSIDIAN  │<───│ CLAUDE CODE │         │
│  │  (Sensors)  │    │   (Memory)  │    │   (Brain)   │         │
│  └─────────────┘    └─────────────┘    └──────┬──────┘         │
│         │                                      │                │
│         │           ┌─────────────┐           │                │
│         └──────────>│     MCP     │<──────────┘                │
│                     │   (Hands)   │                            │
│                     └─────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+ (for Claude Code)
- Claude Code CLI (`npm install -g @anthropic-ai/claude-code`)
- Obsidian (optional, for viewing vault)

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd Digital-Employees

# Create virtual environment (using UV recommended)
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
uv pip install -r requirements.txt

# Or with pip
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your settings
```

### Running the File System Watcher

```bash
# Start the watcher (observer mode - real-time)
python -m src.watchers.filesystem_watcher --vault ./AI_Employee_Vault

# Or polling mode
python -m src.watchers.filesystem_watcher --vault ./AI_Employee_Vault --mode poll --interval 10
```

### Testing

1. Drop a file into `AI_Employee_Vault/Drop/`
2. Watch for action file creation in `AI_Employee_Vault/Needs_Action/`
3. Use Claude Code to process: `/process-inbox`

## Project Structure

```
Digital-Employees/
├── AI_Employee_Vault/           # Obsidian Vault (Memory)
│   ├── Inbox/                   # Raw incoming items
│   ├── Needs_Action/            # Watcher outputs
│   ├── Plans/                   # Claude reasoning outputs
│   ├── Pending_Approval/        # Awaiting human approval
│   ├── Approved/                # Human-approved actions
│   ├── Rejected/                # Human-rejected actions
│   ├── Done/                    # Completed items
│   ├── Logs/                    # JSON audit logs
│   ├── Drop/                    # File drop folder (watched)
│   ├── Dashboard.md             # Real-time status
│   ├── Company_Handbook.md      # Operational rules
│   └── Business_Goals.md        # Objectives
├── src/
│   ├── watchers/                # Input monitors
│   │   ├── base_watcher.py      # Abstract base class
│   │   └── filesystem_watcher.py # File drop watcher
│   ├── mcp_servers/             # Action executors (future)
│   ├── skills/                  # Agent skills (future)
│   └── utils/                   # Shared utilities
├── .claude/
│   └── commands/                # Claude Code skills
│       └── process-inbox.md     # Inbox processing skill
├── config/                      # Configuration files
├── tests/                       # Test suite
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project metadata
└── .env.example                # Environment template
```

## Development Tiers

| Tier | Status | Features |
|------|--------|----------|
| **Bronze** | ✅ Current | Vault + File Watcher + Claude integration |
| Silver | Planned | Gmail + WhatsApp + MCP + HITL + Scheduling |
| Gold | Planned | Full integration + Odoo + CEO Briefing |
| Platinum | Planned | Cloud 24/7 + Multi-agent + Sync |

## Key Principles

1. **Local-First Privacy** - All data stored locally by default
2. **Human-in-the-Loop** - Sensitive actions require approval
3. **Audit Everything** - Every action is logged
4. **Graceful Degradation** - System continues when components fail
5. **Separation of Concerns** - Clear boundaries between perception, reasoning, action

## Claude Code Skills

### `/process-inbox`
Processes all items in `Needs_Action/` folder, creates plans, and routes items appropriately.

```bash
# In Claude Code
/process-inbox
```

## Configuration

### Environment Variables (.env)

```bash
# Required
VAULT_PATH=./AI_Employee_Vault
DRY_RUN=true

# Optional (for future features)
GMAIL_CREDENTIALS_PATH=./config/gmail_credentials.json
WHATSAPP_SESSION_PATH=./config/whatsapp_session
```

## Contributing

See `roadmap.md` for the complete build guide and next steps.

## License

MIT
