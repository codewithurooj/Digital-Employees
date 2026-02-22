"""Test Email MCP in DRY_RUN mode — no real emails sent (Gmail API is mocked)."""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ['DRY_RUN'] = 'true'
os.environ['VAULT_PATH'] = './AI_Employee_Vault'

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 50)
print("EMAIL MCP TEST (DRY RUN / MOCK MODE)")
print("=" * 50)
print("Gmail API calls are mocked — no real emails sent\n")

# ── Import with Gmail API availability check ──────────────────────────────────
try:
    from src.mcp_servers.email_mcp import EmailMCPServer, GMAIL_API_AVAILABLE
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

if not GMAIL_API_AVAILABLE:
    print("Gmail API libraries not installed.")
    print("Install them with:  pip install google-api-python-client google-auth-oauthlib")
    sys.exit(1)

# ── Build a mock Gmail service ────────────────────────────────────────────────
mock_service = MagicMock()
mock_service.users().drafts().create().execute.return_value = {
    'id': 'DRAFT_MOCK_001',
    'message': {'id': 'MSG_MOCK_001', 'threadId': 'THREAD_MOCK_001'}
}
mock_service.users().messages().send().execute.return_value = {
    'id': 'MSG_SENT_MOCK_001',
    'threadId': 'THREAD_MOCK_001'
}

# ── Create server — patch _initialize_service to avoid needing credentials ────
with patch.object(EmailMCPServer, '_initialize_service', lambda self: None):
    server = EmailMCPServer(
        vault_path='./AI_Employee_Vault',
        credentials_path='./config/gmail_credentials.json',
    )

server.service = mock_service  # inject mock Gmail service
server.known_recipients.add('client@example.com')  # bypass unknown-recipient block

# ── Pre-create an Approved file so send_email validation passes ───────────────
vault = Path('./AI_Employee_Vault')
approved_dir = vault / 'Approved'
approved_dir.mkdir(parents=True, exist_ok=True)

approval_id = 'APPROVAL_email_test_20260222'
approved_file = approved_dir / f'{approval_id}.md'
approved_file.write_text(f"""---
type: approval_request
action: send_email
status: approved
approval_id: {approval_id}
---
# Approved: Send Email Test
""")
print(f"Pre-created approved file: {approved_file}\n")

# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: Draft an email (no approval needed)
# ─────────────────────────────────────────────────────────────────────────────
print("TEST 1: Draft an email")
print("-" * 30)
result = server.draft_email(
    to=['client@example.com'],
    subject='Re: Project Update - January 2026',
    body='Dear Client,\n\nThank you for reaching out.\n\nBest regards,\nAI Employee'
)
print(f"Success : {result.success}")
print(f"Status  : {result.status}")
print(f"Draft ID: {result.draft_id}")
if result.error:
    print(f"Error   : {result.error}")
print()

# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: Send an approved email (mocked — nothing actually sent)
# ─────────────────────────────────────────────────────────────────────────────
print("TEST 2: Send email (DRY RUN - mocked)")
print("-" * 30)
result = server.send_email(
    approval_id=approval_id,
    to=['client@example.com'],
    subject='Test Email from AI Employee',
    body='This is a test email sent in dry run mode.\n\nNo real email was sent.'
)
print(f"Success   : {result.success}")
print(f"Status    : {result.status}")
print(f"Message ID: {result.message_id}")
if result.error:
    print(f"Error     : {result.error}")
print()

# ── Cleanup test file ─────────────────────────────────────────────────────────
if approved_file.exists():
    approved_file.unlink()
    print(f"Cleaned up: {approved_file}")

print()
print("=" * 50)
print("TEST COMPLETE")
print("Check AI_Employee_Vault/Logs/ for log entries")
print("=" * 50)
