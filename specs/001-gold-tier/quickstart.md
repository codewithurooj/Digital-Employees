# Quickstart Guide: Gold Tier - Autonomous Employee

**Feature**: Gold Tier
**Date**: 2026-01-25
**Prerequisites**: Silver Tier complete (watchers, HITL, orchestrator, email MCP)

## Overview

This guide walks you through setting up Gold Tier features:
1. Odoo Accounting Integration
2. CEO Briefing Generation
3. Social Media Integration (Facebook, Instagram, Twitter/X)

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Silver Tier fully operational
- [ ] Python 3.11+ installed
- [ ] Odoo Community Edition v19+ accessible
- [ ] Social media accounts with API access (or browser sessions)
- [ ] Playwright installed for browser automation

## Step 1: Environment Configuration

Add these variables to your `.env` file:

```bash
# Odoo Configuration
ODOO_URL=https://your-company.odoo.com
ODOO_DATABASE=your_database_name
ODOO_USERNAME=your_username
ODOO_API_KEY=your_api_key_here
ODOO_SYNC_INTERVAL=300  # 5 minutes

# Social Media - Facebook
FACEBOOK_PAGE_ID=your_page_id
FACEBOOK_ACCESS_TOKEN=your_access_token

# Social Media - Instagram
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_account_id
INSTAGRAM_ACCESS_TOKEN=your_access_token

# Social Media - Twitter/X
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_client_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret

# CEO Briefing
BRIEFING_SCHEDULE="23:00"  # Sunday 11 PM
BRIEFING_TIMEZONE="America/New_York"

# Rate Limits (Gold Tier defaults)
RATE_LIMIT_SOCIAL_POSTS=5  # Per day
```

## Step 2: Odoo Setup

### 2.1 Get Odoo API Key

1. Log into your Odoo instance
2. Go to Settings → Users & Companies → Users
3. Select your user
4. Under "Preferences" tab, click "API Key"
5. Generate a new API key and save it securely

### 2.2 Verify Connection

```bash
# Test Odoo connection
python -c "
from src.lib.odoo_client import OdooClient
client = OdooClient()
print(client.test_connection())
"
```

Expected output: `Connection successful. User ID: <your_uid>`

### 2.3 Initial Sync

```bash
# Run initial invoice sync
python -m src.mcp_servers.odoo_mcp sync_invoices

# Check vault for synced invoices
ls AI_Employee_Vault/Accounting/Invoices/
```

## Step 3: Social Media Setup

### 3.1 Facebook/Instagram (Meta Graph API)

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create an app (Business type)
3. Add "Facebook Login" and "Instagram Basic Display" products
4. Generate a Page Access Token with permissions:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `instagram_basic`
   - `instagram_content_publish`

### 3.2 Twitter/X API

1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a project and app
3. Enable OAuth 2.0
4. Generate access tokens

### 3.3 Browser Fallback (Optional)

If API access is limited, configure Playwright sessions:

```bash
# Install Playwright
pip install playwright
playwright install chromium

# Set up browser sessions (interactive login)
python scripts/setup_social_sessions.py
```

## Step 4: Start Gold Tier Services

### 4.1 Update Orchestrator Configuration

Edit `config/orchestrator.yaml`:

```yaml
enabled_watchers:
  - filesystem
  - gmail
  - whatsapp
  - linkedin
  - odoo  # NEW

mcp_servers:
  - email
  - odoo   # NEW
  - social # NEW

scheduled_tasks:
  ceo_briefing:
    cron: "0 23 * * 0"  # Sunday 11 PM
    skill: ceo_briefing
```

### 4.2 Start the Orchestrator

```bash
# Start in dry-run mode first
DRY_RUN=true python orchestrator.py

# Once verified, run in production
DRY_RUN=false python orchestrator.py
```

## Step 5: Verify Gold Tier Features

### 5.1 Odoo Integration

```bash
# Check Odoo watcher is running
curl http://localhost:8000/health | jq '.watchers.odoo'

# View synced invoices
ls AI_Employee_Vault/Accounting/Invoices/

# View daily transaction log
cat AI_Employee_Vault/Accounting/Transactions/$(date +%Y-%m-%d).md
```

### 5.2 CEO Briefing

```bash
# Generate a test briefing manually
python -c "
from src.skills.ceo_briefing import CEOBriefingSkill
skill = CEOBriefingSkill()
result = skill.generate_briefing()
print(f'Briefing saved to: {result.vault_file}')
"

# View the generated briefing
cat AI_Employee_Vault/Briefings/$(date +%Y-%m-%d)_Monday_Briefing.md
```

### 5.3 Social Media Posting

```bash
# Create a draft post
python -c "
from src.skills.social_posting import SocialPostingSkill
skill = SocialPostingSkill()
draft = skill.create_draft(
    platform='twitter',
    content='Testing Gold Tier social integration! #AIEmployee'
)
print(f'Draft created: {draft.vault_file}')
print(f'Approval required: {draft.approval_required}')
"

# Approve and publish (via HITL workflow)
# 1. Check Pending_Approval folder
# 2. Move approved file to Approved folder
# 3. System will auto-publish
```

## Troubleshooting

### Odoo Connection Issues

```bash
# Check Odoo is reachable
curl -s https://your-company.odoo.com/web/webclient/version_info | jq

# Verify credentials
python -c "
import xmlrpc.client
common = xmlrpc.client.ServerProxy('https://your-company.odoo.com/xmlrpc/2/common')
uid = common.authenticate('database', 'user', 'api_key', {})
print(f'Authenticated: UID={uid}')
"
```

### Social Media Rate Limits

```bash
# Check current rate limit status
curl http://localhost:8002/platforms/twitter/status | jq

# View rate limit errors in logs
grep "rate_limit" AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json
```

### CEO Briefing Not Generating

```bash
# Check scheduler is running
curl http://localhost:8000/health | jq '.scheduled_tasks'

# Check for required data
ls AI_Employee_Vault/Accounting/Invoices/
ls AI_Employee_Vault/Done/
cat AI_Employee_Vault/Business_Goals.md
```

## Common Commands

```bash
# Force Odoo sync
python -m src.mcp_servers.odoo_mcp sync_all

# Generate CEO briefing on demand
python -m src.skills.ceo_briefing generate

# Check social media platform status
python -m src.mcp_servers.social_mcp status

# View audit logs
jq '.' AI_Employee_Vault/Logs/$(date +%Y-%m-%d).json | less

# Check circuit breaker status
curl http://localhost:8000/health | jq '.circuit_breakers'
```

## Security Reminders

1. **Never commit `.env` to version control**
2. **Rotate API keys monthly**
3. **Use separate credentials for dev/prod**
4. **Review audit logs weekly**
5. **Keep social media sessions isolated**

## Next Steps

1. Configure Business_Goals.md with your targets
2. Set up Company_Handbook.md approval rules
3. Run for 1 week in dry-run mode
4. Review CEO briefing accuracy
5. Gradually enable social posting

---

**Need help?** Check the [troubleshooting guide](../docs/troubleshooting.md) or open an issue.
