# Gmail API Setup Guide

Complete guide for setting up Gmail API credentials for the Gmail Watcher.

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Enter project name (e.g., "AI Employee Gmail")
4. Click **Create**

## Step 2: Enable Gmail API

1. In Cloud Console, go to **APIs & Services** → **Library**
2. Search for "Gmail API"
3. Click **Gmail API** → **Enable**

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Select **External** (or Internal if using Google Workspace)
3. Click **Create**
4. Fill in required fields:
   - **App name**: AI Employee
   - **User support email**: Your email
   - **Developer contact**: Your email
5. Click **Save and Continue**

### Scopes

1. Click **Add or Remove Scopes**
2. Add: `https://www.googleapis.com/auth/gmail.readonly`
3. Click **Update** → **Save and Continue**

### Test Users (External only)

1. Click **Add Users**
2. Add your Gmail address
3. Click **Save and Continue**

## Step 4: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Select **Desktop app**
4. Name: "AI Employee Desktop"
5. Click **Create**
6. Click **Download JSON**
7. Save as `config/gmail_credentials.json`

## Step 5: File Structure

```
Digital-Employees/
├── config/
│   ├── gmail_credentials.json  ← Downloaded from Google
│   └── gmail_token.json        ← Auto-created on first auth
└── ...
```

## Step 6: First Run Authentication

```bash
python -m src.watchers.gmail_watcher --vault ./AI_Employee_Vault
```

On first run:
1. Browser opens automatically
2. Log in to your Google account
3. Click "Continue" (ignore "unverified app" warning for personal use)
4. Grant permissions
5. Token saved to `config/gmail_token.json`

## Credentials File Format

`gmail_credentials.json` structure:

```json
{
  "installed": {
    "client_id": "xxx.apps.googleusercontent.com",
    "project_id": "ai-employee-gmail",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "xxx",
    "redirect_uris": ["http://localhost"]
  }
}
```

## Token Refresh

The token auto-refreshes. If issues occur:

```bash
# Delete token and re-authenticate
rm config/gmail_token.json
python -m src.watchers.gmail_watcher --vault ./AI_Employee_Vault
```

## Security Notes

- **Never commit credentials to git**
- Add to `.gitignore`:
  ```
  config/gmail_credentials.json
  config/gmail_token.json
  ```
- Credentials grant read-only access (safe)
- Revoke access anytime at https://myaccount.google.com/permissions

## API Quotas

Gmail API free tier limits:
- 1 billion quota units/day
- `messages.list`: 5 units per call
- `messages.get`: 5 units per call

With default settings (10 emails every 2 minutes):
- ~2,160 calls/day = ~10,800 units/day (well within limits)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Access blocked: unverified app" | Click "Advanced" → "Go to AI Employee (unsafe)" |
| "redirect_uri_mismatch" | Re-download credentials, ensure Desktop app type |
| "Token has been expired or revoked" | Delete `gmail_token.json`, re-authenticate |
| "Quota exceeded" | Wait 24 hours or request quota increase |
| "invalid_grant" | Re-authenticate, check system clock accuracy |

## Scopes Reference

| Scope | Access Level |
|-------|-------------|
| `gmail.readonly` | Read emails only (used by watcher) |
| `gmail.send` | Send emails |
| `gmail.modify` | Read, send, delete, modify |
| `gmail.compose` | Create drafts and send |

The watcher uses `gmail.readonly` for safety - it cannot modify or delete emails.
