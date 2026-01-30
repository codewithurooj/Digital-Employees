# Quickstart Guide: Platinum Tier

**Feature**: Platinum Tier - Always-On Cloud + Local Executive
**Date**: 2026-01-28
**Prerequisites**: Gold Tier fully operational

---

## Overview

The Platinum Tier creates a hybrid Cloud/Local architecture:

- **Cloud Agent**: Runs 24/7 on Oracle Cloud VM, handles email triage, creates drafts
- **Local Agent**: Runs on your machine, handles approvals and sensitive actions
- **Vault Sync**: Git-based synchronization between agents

```
┌─────────────────┐                    ┌─────────────────┐
│   Cloud VM      │                    │  Local Machine  │
│                 │                    │                 │
│  Gmail Watcher  │    Git Sync        │  WhatsApp       │
│  Odoo Monitor   │ ◄─────────────────►│  Approvals      │
│  Draft Creation │    (30s interval)  │  Action Exec    │
│                 │                    │                 │
└─────────────────┘                    └─────────────────┘
```

---

## Prerequisites

Before starting, ensure you have:

1. **Gold Tier Complete**: All Gold Tier features working locally
2. **Oracle Cloud Account**: Free Tier account created at https://cloud.oracle.com
3. **GitHub Account**: For vault synchronization
4. **Domain (Optional)**: For HTTPS (or use IP with self-signed cert)

---

## Part 1: Cloud VM Setup

### 1.1 Create Oracle Cloud VM

1. Log into Oracle Cloud Console
2. Navigate to **Compute > Instances**
3. Click **Create Instance**
4. Configure:
   - **Name**: ai-employee-cloud
   - **Image**: Ubuntu 22.04 (Canonical)
   - **Shape**: VM.Standard.A1.Flex (ARM, 4 OCPU, 24GB RAM - FREE)
   - **Networking**: Create new VCN or use existing
5. Add your SSH public key
6. Click **Create**

### 1.2 Configure Security Group

Add ingress rules:

| Port | Protocol | Source | Description |
|------|----------|--------|-------------|
| 22 | TCP | Your IP | SSH |
| 80 | TCP | 0.0.0.0/0 | HTTP (redirect to HTTPS) |
| 443 | TCP | 0.0.0.0/0 | HTTPS |
| 8069 | TCP | 0.0.0.0/0 | Odoo (optional, via nginx) |

### 1.3 Initial VM Setup

SSH into your new VM:

```bash
ssh ubuntu@<vm-public-ip>
```

Run the setup script:

```bash
# Clone the repository
git clone https://github.com/yourusername/Digital-Employees.git
cd Digital-Employees

# Run cloud setup script
chmod +x deploy/cloud/setup-cloud-vm.sh
./deploy/cloud/setup-cloud-vm.sh
```

The script will install:
- Python 3.11+
- Node.js 24+
- PM2 (process manager)
- Docker + Docker Compose
- Nginx
- Certbot (Let's Encrypt)

---

## Part 2: Vault Synchronization

### 2.1 Create Private GitHub Repository

1. Create new repository: `AI_Employee_Vault` (private)
2. Initialize with README

### 2.2 Configure Local Vault for Git

On your **local machine**:

```bash
cd AI_Employee_Vault

# Initialize Git if not already
git init

# Add remote
git remote add origin git@github.com:yourusername/AI_Employee_Vault.git

# Create .gitignore
cat > .gitignore << 'EOF'
# Secrets - NEVER commit
.env
.env.*
*.env
config/gmail*.json
config/whatsapp_session/
config/*_token*
*.pem
*.key

# System files
__pycache__/
*.pyc
.DS_Store
*.swp
*.swo

# Large files
*.zip
*.tar.gz
*.mp4
*.mov
EOF

# Initial commit
git add .
git commit -m "Initial vault setup"
git push -u origin main
```

### 2.3 Configure Cloud Vault

On the **cloud VM**:

```bash
# Clone vault
git clone git@github.com:yourusername/AI_Employee_Vault.git
cd AI_Employee_Vault

# Configure Git
git config user.email "cloud-agent@yourdomain.com"
git config user.name "Cloud Agent"

# Set up SSH key for automatic push
# (Copy the VM's public key to GitHub as a deploy key with write access)
cat ~/.ssh/id_rsa.pub
```

---

## Part 3: Cloud Environment Configuration

### 3.1 Create Cloud .env

On the **cloud VM**, create `/home/ubuntu/Digital-Employees/.env`:

```bash
# Agent Configuration
AGENT_ID=cloud
WORK_ZONE=cloud
DRY_RUN=false

# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Vault
VAULT_PATH=/home/ubuntu/AI_Employee_Vault

# Gmail (read-only token)
GMAIL_CREDENTIALS_PATH=/home/ubuntu/.config/gmail/credentials.json
GMAIL_TOKEN_PATH=/home/ubuntu/.config/gmail/token.json
GMAIL_CHECK_INTERVAL=120

# Odoo (read-only operations)
ODOO_URL=http://localhost:8069
ODOO_DATABASE=mycompany
ODOO_USERNAME=cloud-agent
ODOO_API_KEY=<read-only-api-key>

# Git Sync
GIT_SYNC_INTERVAL=30
GIT_AUTO_PUSH=true
```

**IMPORTANT**: Do NOT include:
- WhatsApp credentials
- Payment tokens
- Social media posting tokens

### 3.2 Gmail API Setup for Cloud

1. Copy your Gmail credentials to the cloud VM:
   ```bash
   scp config/gmail_credentials.json ubuntu@<vm-ip>:~/.config/gmail/
   ```

2. Generate a new token for cloud-only access (first run will prompt):
   ```bash
   python -c "from src.watchers.gmail_watcher import GmailWatcher; GmailWatcher('/home/ubuntu/AI_Employee_Vault')"
   ```

---

## Part 4: Deploy Odoo to Cloud

### 4.1 Configure Docker Compose

Edit `deploy/cloud/docker-compose.yml`:

```yaml
version: '3.8'
services:
  odoo:
    image: odoo:19.0
    depends_on:
      - db
    ports:
      - "127.0.0.1:8069:8069"
    volumes:
      - odoo-data:/var/lib/odoo
      - ./odoo.conf:/etc/odoo/odoo.conf
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

### 4.2 Start Odoo

```bash
cd deploy/cloud

# Create .env for Odoo
echo "POSTGRES_PASSWORD=$(openssl rand -hex 16)" > .env

# Start services
docker-compose up -d

# Check status
docker-compose ps
```

### 4.3 Configure Nginx for HTTPS

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate (replace with your domain)
sudo certbot --nginx -d ai-employee.yourdomain.com

# Or for IP only (self-signed):
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/nginx-selfsigned.key \
  -out /etc/ssl/certs/nginx-selfsigned.crt
```

---

## Part 5: Start Cloud Agent

### 5.1 Configure PM2

Create `deploy/cloud/ecosystem.config.js`:

```javascript
module.exports = {
  apps: [
    {
      name: 'cloud-orchestrator',
      script: 'python',
      args: '-m src.cloud.cloud_orchestrator',
      cwd: '/home/ubuntu/Digital-Employees',
      interpreter: 'none',
      env: {
        PYTHONPATH: '/home/ubuntu/Digital-Employees'
      },
      max_restarts: 10,
      autorestart: true,
      watch: false
    },
    {
      name: 'health-monitor',
      script: 'python',
      args: '-m src.cloud.health_monitor',
      cwd: '/home/ubuntu/Digital-Employees',
      interpreter: 'none',
      cron_restart: '0 */6 * * *',
      autorestart: true
    }
  ]
};
```

### 5.2 Start Services

```bash
cd /home/ubuntu/Digital-Employees

# Start with PM2
pm2 start deploy/cloud/ecosystem.config.js

# Enable startup on boot
pm2 startup
pm2 save

# Check status
pm2 status
pm2 logs cloud-orchestrator
```

---

## Part 6: Configure Local Agent

### 6.1 Update Local .env

Add to your **local** `.env`:

```bash
# Agent Configuration
AGENT_ID=local
WORK_ZONE=local

# Vault Sync
GIT_AUTO_PULL=true
GIT_PULL_INTERVAL=60

# Cloud Odoo URL (for viewing)
ODOO_URL=https://ai-employee.yourdomain.com
```

### 6.2 Start Local Agent

```bash
cd Digital-Employees

# Pull latest from vault
cd AI_Employee_Vault && git pull && cd ..

# Start local orchestrator
python orchestrator.py --vault ./AI_Employee_Vault --live --watchers filesystem whatsapp linkedin
```

---

## Part 7: Verify Setup

### 7.1 Check Cloud Agent

```bash
# On cloud VM
pm2 status
pm2 logs cloud-orchestrator --lines 50

# Check health status
cat ~/AI_Employee_Vault/Health/status.md
```

### 7.2 Check Sync

```bash
# On local machine
cd AI_Employee_Vault
git pull
ls -la In_Progress/cloud/  # Should see any cloud-claimed tasks
```

### 7.3 Test End-to-End

1. Send yourself an important email
2. Wait for cloud agent to create draft (check `/Pending_Approval/email/`)
3. On local machine, pull changes: `cd AI_Employee_Vault && git pull`
4. Move approval file: `mv Pending_Approval/email/DRAFT_*.md Approved/email/`
5. Local agent sends email
6. Verify in `/Done/`

---

## Troubleshooting

### Cloud Agent Not Starting

```bash
# Check PM2 logs
pm2 logs cloud-orchestrator

# Check environment
cat /home/ubuntu/Digital-Employees/.env

# Restart
pm2 restart cloud-orchestrator
```

### Git Sync Failing

```bash
# Check sync state
cat ~/AI_Employee_Vault/Health/sync_state.json

# Manual sync test
cd ~/AI_Employee_Vault
git pull
git status
```

### Odoo Not Accessible

```bash
# Check Docker
docker-compose ps
docker-compose logs odoo

# Check nginx
sudo nginx -t
sudo systemctl status nginx
```

---

## Security Checklist

- [ ] SSH key-only authentication (disable password)
- [ ] Firewall configured (only needed ports open)
- [ ] .gitignore excludes all secrets
- [ ] Cloud .env has minimal credentials
- [ ] WhatsApp session NOT on cloud
- [ ] Payment tokens NOT on cloud
- [ ] HTTPS enabled for Odoo

---

## Next Steps

1. Monitor cloud agent for 24 hours
2. Check Health/status.md regularly
3. Process approval backlog on local return
4. Review audit logs in /Logs/

---

**Setup Complete!** Your AI Employee now operates 24/7.
