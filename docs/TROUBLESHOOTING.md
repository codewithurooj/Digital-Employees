# Troubleshooting Guide - Platinum Tier

## Common Issues

---

### Cloud Agent Not Starting

**Symptoms**: PM2 shows `errored` or `stopped` status.

```bash
# Check logs
pm2 logs cloud-orchestrator --lines 50

# Check environment
python -c "import dotenv; dotenv.load_dotenv(); import os; print(os.environ.get('VAULT_PATH'))"

# Verify Python path
which python
python --version  # Must be 3.11+

# Restart
pm2 restart cloud-orchestrator
```

**Common causes**:
- Missing `.env` file or variables
- Python version too old
- Missing dependencies (`uv pip install -r requirements.txt`)
- Vault path doesn't exist

---

### Git Sync Failing

**Symptoms**: Changes not appearing on the other agent. `Health/sync_state.json` shows failures.

```bash
# Check sync state
cat AI_Employee_Vault/Health/sync_state.json

# Manual sync test
cd AI_Employee_Vault
git status
git pull --rebase
git push

# Check SSH key
ssh -T git@github.com

# Check remote
git remote -v
```

**Common causes**:
- SSH key not added to GitHub as deploy key
- Merge conflicts (check `git status`)
- Network connectivity issues
- Repository permissions

**Fix merge conflicts**:
```bash
cd AI_Employee_Vault
git stash
git pull
git stash pop
# Resolve any conflicts manually
git add .
git commit -m "resolve sync conflict"
git push
```

---

### Work-Zone Violations

**Symptoms**: `WorkZoneViolation` errors in logs.

This means the cloud agent attempted an action that requires local execution (sending emails, publishing posts, executing payments).

```bash
# Check audit log for violations
grep "work_zone_violation" AI_Employee_Vault/Logs/*.jsonl
```

**This is expected behavior** - the cloud agent correctly blocked itself. The action will be queued in `Pending_Approval/` for the local agent.

---

### Odoo Not Accessible

**Symptoms**: Can't reach Odoo web interface or API errors.

```bash
# Check Docker containers
cd deploy/cloud
docker-compose ps
docker-compose logs odoo --tail 50
docker-compose logs db --tail 50

# Check if port is listening
ss -tlnp | grep 8069

# Check nginx proxy
sudo nginx -t
sudo systemctl status nginx
sudo tail -20 /var/log/nginx/error.log

# Restart Odoo
docker-compose restart odoo
```

**Common causes**:
- Docker not running (`sudo systemctl start docker`)
- PostgreSQL out of disk space
- Nginx misconfiguration
- Port conflict

---

### Email Triage Not Working

**Symptoms**: Emails not being triaged, no drafts in `Pending_Approval/email/`.

```bash
# Check Gmail watcher status
grep "gmail" AI_Employee_Vault/Logs/*.jsonl | tail -10

# Check Gmail API credentials
ls -la ~/.config/gmail/
python -c "from google.oauth2.credentials import Credentials; c = Credentials.from_authorized_user_file('config/gmail_token.json'); print('Valid:', c.valid)"

# Check Needs_Action/email folder
ls AI_Employee_Vault/Needs_Action/email/
```

**Common causes**:
- Gmail token expired (delete token, re-authenticate)
- Gmail API quota exceeded
- No new emails matching query filter

---

### Dashboard Not Updating

**Symptoms**: `Dashboard.md` not reflecting latest status.

The Dashboard is only written by the **local agent** (single-writer rule). The cloud agent writes to `/Updates/` which the local agent merges.

```bash
# Check for pending updates
ls AI_Employee_Vault/Updates/

# On local machine, trigger merge
python -c "from src.local.dashboard_merger import DashboardMerger; m = DashboardMerger('./AI_Employee_Vault'); print(m.merge_all_pending())"
```

---

### High Resource Usage

**Symptoms**: Health status shows `warning` or `critical`.

```bash
# Check resources
pm2 monit

# Check disk space
df -h

# Check memory
free -h

# Check for runaway processes
top -o %MEM

# Clean up old logs
find AI_Employee_Vault/Logs -name "*.json*" -mtime +30 -delete

# Clean Docker
docker system prune -f
```

**Thresholds**:
| Metric | Warning | Critical |
|--------|---------|----------|
| CPU | 70% | 90% |
| Memory | 80% | 95% |
| Disk | 85% | 95% |

---

### Claim Conflicts

**Symptoms**: Two agents try to claim the same task.

The claim-by-move protocol resolves this automatically - first successful Git push wins. The losing agent's claim is rejected.

```bash
# Check active claims
ls AI_Employee_Vault/In_Progress/cloud/
ls AI_Employee_Vault/In_Progress/local/

# Check for expired claims (>15 min)
grep "claim_expires" AI_Employee_Vault/In_Progress/**/*.md
```

---

## Diagnostic Commands

```bash
# Full system check
pm2 status
docker-compose ps
cat AI_Employee_Vault/Health/status.md
git -C AI_Employee_Vault status

# Test connectivity
curl -s http://localhost:8069/web/database/list  # Odoo
ssh -T git@github.com                            # GitHub

# Check all logs from today
cat AI_Employee_Vault/Logs/$(date +%Y-%m-%d).jsonl | python -m json.tool

# Run test suite
python -m pytest tests/ -v --tb=short
```

---

## Getting Help

1. Check logs first: `pm2 logs` and `AI_Employee_Vault/Logs/`
2. Run the test suite: `python -m pytest tests/ -v`
3. Review Health status: `AI_Employee_Vault/Health/status.md`
4. Check Git sync state: `AI_Employee_Vault/Health/sync_state.json`
