# Playwright Setup Guide

Complete guide for setting up Playwright for WhatsApp Watcher.

## Step 1: Install Playwright

```bash
# Install Playwright Python package
pip install playwright

# Install browser (Chromium recommended for WhatsApp Web)
playwright install chromium
```

## Step 2: Verify Installation

```bash
# Check Playwright is installed
python -c "from playwright.sync_api import sync_playwright; print('Playwright OK')"

# Check browser is installed
playwright --version
```

## Step 3: First Run - QR Authentication

```bash
# Run with visible browser
python -m src.watchers.whatsapp_watcher --vault ./AI_Employee_Vault
```

**What happens:**
1. Chromium browser opens
2. Navigates to https://web.whatsapp.com
3. QR code displayed
4. Open WhatsApp on your phone
5. Go to Settings → Linked Devices → Link a Device
6. Scan QR code
7. Session saved to `config/whatsapp_session/`

## Session Persistence

After first login, your session is stored:

```
config/whatsapp_session/
├── Default/
│   ├── Cache/
│   ├── Cookies
│   ├── Local Storage/
│   └── Session Storage/
└── ...
```

**Important**: Keep this folder secure - it contains your WhatsApp session.

## Running Headless (After Login)

Once authenticated, run without visible browser:

```bash
python -m src.watchers.whatsapp_watcher --vault ./AI_Employee_Vault --headless
```

## Troubleshooting

### Browser Won't Start

```bash
# Reinstall browser
playwright install chromium --force

# Try with dependencies
playwright install-deps chromium
```

### Session Expired

WhatsApp sessions can expire. Re-authenticate:

```bash
# Delete old session
rm -rf config/whatsapp_session

# Run again (will show QR code)
python -m src.watchers.whatsapp_watcher --vault ./AI_Employee_Vault
```

### "Target closed" Error

Browser crashed or was closed. Check:
- Enough system memory (Chromium needs ~500MB)
- No conflicting browser instances
- Try without `--headless` to see what's happening

### WhatsApp Web UI Changed

WhatsApp occasionally updates their web interface. If messages aren't being detected:

1. Check browser console for errors
2. Inspect element selectors in `whatsapp_watcher.py`
3. Update selectors if WhatsApp changed their HTML

### Slow Performance

```bash
# Increase check interval
python -m src.watchers.whatsapp_watcher --vault ./AI_Employee_Vault --interval 60
```

## Browser Arguments

The watcher uses these Chromium arguments:

```python
args=[
    '--disable-blink-features=AutomationControlled',  # Avoid detection
    '--no-sandbox'  # Required for some environments
]
```

## Running on Server (Headless Linux)

For servers without display:

```bash
# Install dependencies
playwright install-deps chromium

# Run headless (after local QR auth)
python -m src.watchers.whatsapp_watcher --vault ./AI_Employee_Vault --headless
```

**Note**: You must do initial QR scan on a machine with display, then copy the session folder to server.

## Security Considerations

1. **Session folder**: Contains your WhatsApp auth - treat as sensitive
2. **Don't share**: Never commit `config/whatsapp_session/` to git
3. **Add to .gitignore**:
   ```
   config/whatsapp_session/
   ```
4. **Revoke access**: In WhatsApp mobile → Linked Devices → Remove device

## Multiple Accounts

Each account needs a separate session folder:

```bash
# Account 1
python -m src.watchers.whatsapp_watcher --vault ./Vault1 --session ./sessions/account1

# Account 2
python -m src.watchers.whatsapp_watcher --vault ./Vault2 --session ./sessions/account2
```

## API Reference

### WhatsAppWatcher Class

```python
WhatsAppWatcher(
    vault_path: str,              # Required: Obsidian vault path
    session_path: str = None,     # Browser session storage
    check_interval: int = 30,     # Seconds between checks
    keywords: List[str] = None,   # Trigger keywords
    headless: bool = False,       # Run without GUI
    contacts_whitelist: List[str] = None  # Monitor only these contacts
)
```

### Methods

| Method | Description |
|--------|-------------|
| `run()` | Start monitoring loop |
| `stop()` | Stop watcher and close browser |
| `check_for_updates()` | Single check for new messages |
| `create_action_file(item)` | Create action file from message |

## Environment Variables

Optional environment configuration:

```bash
# Custom Playwright browser path
PLAYWRIGHT_BROWSERS_PATH=/custom/path

# Skip browser download
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
```
