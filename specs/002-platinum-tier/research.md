# Research: Platinum Tier - Always-On Cloud + Local Executive

**Feature**: Platinum Tier
**Date**: 2026-01-28
**Status**: Complete

## Research Tasks

### 1. Cloud Provider Selection

#### Question
Which cloud provider is best for 24/7 always-on deployment with minimal cost?

#### Findings

**Options Evaluated**:

1. **Oracle Cloud Free Tier** (RECOMMENDED)
   - ARM64 Ampere A1: 4 OCPUs, 24GB RAM (free forever)
   - AMD64: 1/8 OCPU, 1GB RAM (free forever)
   - 200GB block storage
   - 10TB outbound data/month
   - Always Free (not trial)

2. **AWS Free Tier**
   - t2.micro: 1 vCPU, 1GB RAM
   - 12-month free trial only
   - Limited after trial period
   - $8-15/month for comparable specs

3. **Google Cloud Free Tier**
   - e2-micro: 0.25 vCPU, 1GB RAM
   - US regions only for free
   - Insufficient for Odoo

4. **DigitalOcean**
   - $4/month for 512MB RAM
   - No free tier
   - Good reliability

#### Decision
**Oracle Cloud Free Tier (ARM64 Ampere A1)**

**Rationale**:
- 24GB RAM supports Odoo + watchers comfortably
- ARM64 compatible with Python, Node.js, Docker
- Truly free (not time-limited)
- Adequate network bandwidth
- Supports Ubuntu 22.04 LTS

#### Specs Comparison

| Provider | vCPU | RAM | Storage | Cost |
|----------|------|-----|---------|------|
| Oracle (ARM) | 4 | 24GB | 200GB | Free |
| AWS t2.micro | 1 | 1GB | 30GB | $8/mo after trial |
| GCP e2-micro | 0.25 | 1GB | 30GB | Free (limited) |
| DigitalOcean | 1 | 1GB | 25GB | $6/mo |

---

### 2. Process Management for 24/7 Reliability

#### Question
How to ensure cloud processes stay running with automatic recovery?

#### Findings

**Options Evaluated**:

1. **PM2** (RECOMMENDED)
   - Node.js process manager (works for Python too)
   - Auto-restart on crash
   - Log management and rotation
   - Cluster mode for Node apps
   - Startup script generation
   - Built-in monitoring dashboard

2. **systemd**
   - Native Linux service manager
   - Auto-restart capability
   - More complex configuration
   - Less visibility into process state

3. **Supervisor**
   - Python-based process control
   - Similar to PM2
   - Less active development
   - XML configuration (verbose)

4. **Docker + Docker Compose**
   - Container orchestration
   - restart: always policy
   - Heavier resource usage
   - Adds complexity

#### Decision
**PM2 for watchers/orchestrator + Docker Compose for Odoo**

**Rationale**:
- PM2 excels at Node/Python process management
- Easy startup script generation (`pm2 startup`)
- Built-in log rotation
- Docker Compose isolates Odoo + PostgreSQL
- Best of both worlds without Kubernetes complexity

#### PM2 Configuration Example
```javascript
// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: 'cloud-orchestrator',
      script: 'python',
      args: 'src/cloud/cloud_orchestrator.py --vault ./AI_Employee_Vault',
      cwd: '/home/ubuntu/Digital-Employees',
      interpreter: 'none',
      env: {
        PYTHONPATH: '/home/ubuntu/Digital-Employees',
        DRY_RUN: 'false',
        AGENT_ID: 'cloud'
      },
      max_restarts: 10,
      restart_delay: 5000,
      autorestart: true
    },
    {
      name: 'health-monitor',
      script: 'python',
      args: 'src/cloud/health_monitor.py',
      cwd: '/home/ubuntu/Digital-Employees',
      interpreter: 'none',
      cron_restart: '0 */6 * * *',  // Restart every 6 hours
      autorestart: true
    }
  ]
};
```

---

### 3. Vault Synchronization Strategy

#### Question
How to synchronize the Obsidian vault between cloud and local agents?

#### Findings

**Options Evaluated**:

1. **Git Push/Pull** (RECOMMENDED)
   - Version control built-in
   - Works offline
   - Conflict detection
   - Audit trail via commits
   - GitHub/GitLab free private repos

2. **Syncthing**
   - Peer-to-peer sync
   - Real-time
   - No central server
   - Conflicts are file-level (entire file)
   - No audit trail

3. **Rsync**
   - One-way sync
   - Efficient delta transfer
   - No conflict handling
   - Requires SSH tunnel

4. **Cloud Storage (S3/GCS)**
   - Central storage
   - SDK complexity
   - Cost for storage
   - No native conflict resolution

#### Decision
**Git with GitHub private repository**

**Rationale**:
- Perfect for markdown vault (text files)
- Commit history provides audit trail
- Branch protection prevents accidental overwrites
- Works when either agent is offline
- Free private repos on GitHub
- Familiar tooling

#### Sync Protocol
```python
# Cloud agent: Push after task completion
def sync_push():
    """Push changes after task completion."""
    subprocess.run(['git', 'add', '-A'], check=True)
    subprocess.run(['git', 'commit', '-m', f'cloud: {task_summary}'], check=False)
    subprocess.run(['git', 'push', 'origin', 'main'], check=True)

# Local agent: Pull on startup and periodically
def sync_pull():
    """Pull latest changes from remote."""
    result = subprocess.run(['git', 'pull', '--rebase', 'origin', 'main'],
                          capture_output=True, text=True)
    if 'CONFLICT' in result.stderr:
        handle_conflict(result.stderr)
    return result.returncode == 0
```

#### Conflict Prevention: Claim-by-Move
```text
1. Task file exists in /Needs_Action/email/TASK_001.md
2. Cloud agent attempts to claim:
   - git pull (sync first)
   - Move file to /In_Progress/cloud/TASK_001.md
   - git add, commit, push
3. If push fails (conflict):
   - Another agent claimed first
   - Abandon claim, continue to next task
4. If push succeeds:
   - Task is now owned by cloud agent
   - Other agents will see it in /In_Progress/cloud/
```

---

### 4. Work-Zone Specialization Architecture

#### Question
How to enforce cloud vs local action boundaries?

#### Findings

**Work-Zone Matrix** (from spec):

| Action Type | Cloud Allowed | Local Required |
|------------|---------------|----------------|
| Read files | ✅ | - |
| Create drafts | ✅ | - |
| Write to /Needs_Action | ✅ | - |
| Write to /Updates | ✅ | - |
| Git sync | ✅ | - |
| Create approval requests | ✅ | - |
| Process approvals | ❌ | ✅ |
| Send emails | ❌ | ✅ |
| Post to social media | ❌ | ✅ |
| Execute payments | ❌ | ✅ |
| WhatsApp operations | ❌ | ✅ |
| Update Dashboard.md | ❌ | ✅ (single-writer) |

**Implementation Options**:

1. **Decorator-based enforcement** (RECOMMENDED)
   - Python decorators on MCP methods
   - Raises WorkZoneViolation if cloud attempts local action
   - Clear, auditable, fail-fast

2. **Configuration-based**
   - YAML config specifying allowed actions
   - Less compile-time safety
   - Easier to modify

3. **Separate MCP implementations**
   - CloudEmailMCP vs LocalEmailMCP
   - Code duplication
   - Harder to maintain

#### Decision
**Decorator-based enforcement with audit logging**

**Rationale**:
- Single source of truth for action permissions
- Fail-fast prevents accidental execution
- Audit log captures blocked attempts
- Easy to test

#### Implementation Pattern
```python
from functools import wraps
from enum import Enum

class WorkZone(Enum):
    CLOUD = 'cloud'
    LOCAL = 'local'

def requires_local(func):
    """Decorator to enforce local-only execution."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.agent_zone == WorkZone.CLOUD:
            self.logger.warning(
                f"BLOCKED: {func.__name__} requires local agent"
            )
            self.audit_log('work_zone_violation', {
                'action': func.__name__,
                'zone': 'cloud',
                'required': 'local'
            })
            raise WorkZoneViolation(f"{func.__name__} requires local agent")
        return func(self, *args, **kwargs)
    return wrapper

class EmailMCP:
    def __init__(self, agent_zone: WorkZone):
        self.agent_zone = agent_zone

    def draft_email(self, to, subject, body):
        """Cloud and local can draft."""
        # ... create draft

    @requires_local
    def send_email(self, draft_id):
        """Only local can send."""
        # ... send email
```

---

### 5. Odoo Cloud Deployment

#### Question
How to deploy Odoo Community Edition on cloud VM?

#### Findings

**Deployment Options**:

1. **Docker Compose** (RECOMMENDED)
   - Official Odoo Docker image
   - PostgreSQL container
   - Easy backup/restore
   - Reproducible environment

2. **Native installation**
   - apt/yum packages
   - Manual PostgreSQL setup
   - Harder to isolate

3. **Odoo.sh**
   - Managed hosting
   - Not free
   - Overkill for single-user

#### Decision
**Docker Compose with nginx reverse proxy**

**Rationale**:
- Isolated environment
- Easy version upgrades
- Backup = dump PostgreSQL + copy filestore
- HTTPS via nginx + Let's Encrypt

#### Docker Compose Configuration
```yaml
# docker-compose.yml
version: '3.8'
services:
  odoo:
    image: odoo:19.0
    depends_on:
      - db
    ports:
      - "8069:8069"
    volumes:
      - odoo-data:/var/lib/odoo
      - ./config:/etc/odoo
      - ./addons:/mnt/extra-addons
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=${POSTGRES_PASSWORD}

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  odoo-data:
  postgres-data:
```

#### Backup Script
```bash
#!/bin/bash
# backup-cron.sh - Run daily via cron
DATE=$(date +%Y%m%d)
BACKUP_DIR=/backup/odoo

# Backup PostgreSQL
docker exec postgres pg_dump -U odoo odoo > $BACKUP_DIR/db_$DATE.sql

# Backup filestore
tar -czf $BACKUP_DIR/filestore_$DATE.tar.gz /var/lib/docker/volumes/odoo-data

# Cleanup backups older than 7 days
find $BACKUP_DIR -mtime +7 -delete
```

---

### 6. Health Monitoring Implementation

#### Question
How to monitor cloud agent health and auto-recover from failures?

#### Findings

**Monitoring Requirements**:
1. Process status (running/stopped/crashed)
2. API connectivity (Gmail, Odoo)
3. Resource usage (CPU, memory, disk)
4. Git sync status
5. Alert on critical failures

**Options Evaluated**:

1. **Custom Python health monitor** (RECOMMENDED)
   - Integrates with existing codebase
   - Writes to vault /Health folder
   - PM2 restart via subprocess

2. **Prometheus + Grafana**
   - Industry standard
   - Overkill for single-agent
   - Requires additional infrastructure

3. **Uptime Robot / External monitoring**
   - External availability checks
   - Free tier available
   - No internal process visibility

#### Decision
**Custom health monitor + PM2 + simple external ping**

**Rationale**:
- Custom monitor for deep health checks
- PM2 handles restarts
- External ping (UptimeRobot) for cloud VM availability
- Writes status to vault for visibility

#### Health Monitor Implementation
```python
class HealthMonitor:
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.health_file = vault_path / 'Health' / 'status.md'
        self.check_interval = 60  # seconds

    def check_process(self, name: str) -> bool:
        """Check if PM2 process is running."""
        result = subprocess.run(
            ['pm2', 'show', name, '--silent'],
            capture_output=True
        )
        return result.returncode == 0

    def check_api(self, service: str) -> bool:
        """Check API connectivity."""
        if service == 'gmail':
            # Test Gmail API
            pass
        elif service == 'odoo':
            # Test Odoo JSON-RPC
            pass
        return True

    def get_resources(self) -> dict:
        """Get system resource usage."""
        import psutil
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        }

    def restart_process(self, name: str):
        """Restart a failed process via PM2."""
        subprocess.run(['pm2', 'restart', name])
        self.log_event('process_restarted', {'name': name})

    def write_status(self, status: dict):
        """Write health status to vault."""
        content = f'''# Health Status

> Last Check: {datetime.now().isoformat()}

## Processes

| Process | Status |
|---------|--------|
| cloud-orchestrator | {'🟢 Running' if status['orchestrator'] else '🔴 Stopped'} |
| health-monitor | 🟢 Running |

## API Connectivity

| Service | Status |
|---------|--------|
| Gmail API | {'🟢 OK' if status['gmail'] else '🔴 Error'} |
| Odoo API | {'🟢 OK' if status['odoo'] else '🔴 Error'} |

## Resources

| Metric | Value | Threshold |
|--------|-------|-----------|
| CPU | {status['cpu']}% | <80% |
| Memory | {status['memory']}% | <85% |
| Disk | {status['disk']}% | <90% |

## Recent Incidents

{status.get('incidents', 'None')}
'''
        self.health_file.write_text(content)
```

---

### 7. Secret Management for Cloud/Local Split

#### Question
How to manage secrets with zero exposure on cloud?

#### Findings

**Secret Categories**:

| Secret Type | Cloud Allowed | Local Only |
|-------------|---------------|------------|
| ANTHROPIC_API_KEY | ✅ | ✅ |
| GMAIL_CREDENTIALS_PATH | ✅ (read-only token) | ✅ |
| ODOO_API_KEY | ✅ (read-only) | ✅ |
| WHATSAPP_SESSION | ❌ | ✅ |
| PAYMENT_TOKENS | ❌ | ✅ |
| BANKING_CREDENTIALS | ❌ | ✅ |
| SOCIAL_POST_TOKENS | ❌ (drafts only) | ✅ |

**Implementation**:

1. **Cloud .env (minimal)**
   ```
   AGENT_ID=cloud
   ANTHROPIC_API_KEY=sk-ant-...
   GMAIL_CREDENTIALS_PATH=/etc/credentials/gmail.json
   ODOO_URL=http://localhost:8069
   ODOO_DATABASE=mycompany
   ODOO_API_KEY=...  # Read-only operations
   DRY_RUN=false
   WORK_ZONE=cloud
   ```

2. **Local .env (full)**
   ```
   AGENT_ID=local
   ANTHROPIC_API_KEY=sk-ant-...
   GMAIL_CREDENTIALS_PATH=./config/gmail.json
   ODOO_URL=https://cloud-vm:8069
   ODOO_DATABASE=mycompany
   ODOO_API_KEY=...  # Full access
   WHATSAPP_SESSION_PATH=./config/whatsapp_session
   PAYMENT_GATEWAY_TOKEN=...
   FACEBOOK_ACCESS_TOKEN=...
   TWITTER_API_KEY=...
   DRY_RUN=false
   WORK_ZONE=local
   ```

3. **.gitignore enforcement**
   ```gitignore
   # Secrets - NEVER commit
   .env
   .env.*
   *.env
   config/gmail*.json
   config/whatsapp_session/
   config/*_token*
   *.pem
   *.key

   # Cloud-specific
   deploy/cloud/.env
   ```

#### Decision
**Strict .gitignore + separate .env files + pre-commit hook**

**Rationale**:
- .gitignore prevents accidental commits
- Pre-commit hook fails on secret patterns
- Clear separation of cloud vs local secrets
- Minimal cloud footprint

---

## Alternatives Considered

| Decision | Alternative | Why Rejected |
|----------|-------------|--------------|
| Oracle Cloud | AWS/GCP | Free tier limitations; cost after trial |
| PM2 | systemd | Less visibility; harder log management |
| Git sync | Syncthing | No version control; conflict handling |
| Docker for Odoo | Native install | Harder to backup/restore; less isolated |
| Custom health | Prometheus | Overkill; infrastructure overhead |

## Open Questions (Resolved)

1. **Q**: What if both agents try to claim the same task?
   **A**: Claim-by-move with Git push. First successful push wins. Loser sees conflict on their push and abandons.

2. **Q**: How to handle cloud offline (VM reboot)?
   **A**: PM2 startup script auto-starts processes on boot. Local continues operating independently.

3. **Q**: What if Git conflicts occur in Dashboard.md?
   **A**: Single-writer rule: only local writes to Dashboard.md. Cloud writes to /Updates; local merges.

4. **Q**: How to handle WhatsApp session expiry?
   **A**: Local-only operation. Manual re-authentication documented. Alert when session fails.

5. **Q**: Odoo database backup strategy?
   **A**: Daily pg_dump via cron. 7-day retention. Weekly test restore.

---

**Research Status**: COMPLETE - All unknowns resolved, ready for Phase 1 design.
