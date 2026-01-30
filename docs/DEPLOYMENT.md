# Deployment Guide - Platinum Tier

## Overview

The Platinum Tier deploys two agents:
- **Cloud Agent**: Oracle Cloud VM (24/7)
- **Local Agent**: Your local machine (on-demand)

Both share state through a Git-synchronized Obsidian vault.

---

## Cloud Agent Deployment

### 1. VM Provisioning

**Recommended**: Oracle Cloud Free Tier ARM instance

| Setting | Value |
|---------|-------|
| Shape | VM.Standard.A1.Flex |
| OCPU | 4 (free) |
| RAM | 24 GB (free) |
| OS | Ubuntu 22.04 |
| Storage | 200 GB boot volume |

```bash
# SSH into the VM
ssh ubuntu@<vm-public-ip>

# Clone repository
git clone https://github.com/yourusername/Digital-Employees.git
cd Digital-Employees

# Run setup script
chmod +x deploy/cloud/setup-cloud-vm.sh
./deploy/cloud/setup-cloud-vm.sh
```

### 2. Environment Configuration

Create `.env` on the cloud VM:

```bash
cp deploy/cloud/.env.example .env
# Edit with your values
nano .env
```

Required variables:
- `AGENT_ID=cloud`
- `WORK_ZONE=cloud`
- `ANTHROPIC_API_KEY=sk-ant-...`
- `VAULT_PATH=/home/ubuntu/AI_Employee_Vault`

**Never include** on cloud: WhatsApp credentials, payment tokens, social media posting tokens.

### 3. Vault Synchronization

```bash
# Clone the vault repo
git clone git@github.com:yourusername/AI_Employee_Vault.git

# Configure Git identity
cd AI_Employee_Vault
git config user.email "cloud-agent@yourdomain.com"
git config user.name "Cloud Agent"
```

### 4. Odoo Deployment (Optional)

```bash
cd deploy/cloud

# Set Postgres password
echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)" > .env

# Start Odoo + PostgreSQL
docker-compose up -d

# Verify
docker-compose ps
curl http://localhost:8069
```

### 5. Start Cloud Agent

```bash
# Start with PM2
pm2 start deploy/cloud/ecosystem.config.js

# Enable auto-start on reboot
pm2 startup
pm2 save

# Verify
pm2 status
pm2 logs cloud-orchestrator --lines 20
```

### 6. Nginx + HTTPS

```bash
# Copy nginx config
sudo cp deploy/cloud/nginx.conf /etc/nginx/sites-available/ai-employee
sudo ln -s /etc/nginx/sites-available/ai-employee /etc/nginx/sites-enabled/

# Get SSL certificate
sudo certbot --nginx -d ai-employee.yourdomain.com

# Reload
sudo nginx -t && sudo systemctl reload nginx
```

---

## Local Agent Deployment

### 1. Update Local Environment

Add to your `.env`:

```bash
AGENT_ID=local
WORK_ZONE=local
GIT_AUTO_PULL=true
GIT_PULL_INTERVAL=60
```

### 2. Start Local Agent

```bash
# Pull latest vault state
cd AI_Employee_Vault && git pull && cd ..

# Start local orchestrator
python -m src.local --vault ./AI_Employee_Vault

# Or in live mode (execute actions)
python -m src.local --vault ./AI_Employee_Vault --live
```

---

## Backup & Recovery

### Automated Backups

The cloud VM runs daily backups via cron:

```bash
# Backup script location
deploy/cloud/backup-cron.sh

# Manual backup
./deploy/cloud/backup-cron.sh
```

Backups include:
- PostgreSQL database dump
- Odoo filestore
- 7-day retention

### Recovery

```bash
# Restore PostgreSQL
docker exec -i cloud-db psql -U odoo postgres < backup_20260130.sql

# Restore vault from Git
cd AI_Employee_Vault
git log  # Find the commit to restore to
git checkout <commit-hash> -- .
```

---

## Monitoring

### Health Status

Check `AI_Employee_Vault/Health/status.md` for:
- CPU/Memory/Disk usage
- Recent incidents
- Overall status (healthy/warning/critical)

### PM2 Dashboard

```bash
pm2 monit          # Real-time monitoring
pm2 status         # Process overview
pm2 logs           # All logs
pm2 logs cloud-orchestrator --lines 100
```

### Log Files

```bash
# Application logs
ls AI_Employee_Vault/Logs/

# PM2 logs
ls ~/.pm2/logs/

# Nginx logs
sudo tail -f /var/log/nginx/access.log
```

---

## Security Checklist

- [ ] SSH key-only authentication enabled
- [ ] Password authentication disabled
- [ ] UFW firewall active (ports 22, 80, 443 only)
- [ ] `.gitignore` excludes all secrets
- [ ] Cloud `.env` has minimal credentials
- [ ] WhatsApp credentials NOT on cloud
- [ ] Payment tokens NOT on cloud
- [ ] HTTPS enabled
- [ ] Odoo accessible only via nginx proxy
- [ ] PostgreSQL not exposed externally

---

## Updating

```bash
# On cloud VM
cd Digital-Employees
git pull

# Restart services
pm2 restart all

# If dependencies changed
uv pip install -r requirements.txt
```
