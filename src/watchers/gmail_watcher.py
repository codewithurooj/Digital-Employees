"""
Gmail Watcher - Monitors Gmail for important/unread emails.

Requires Google API credentials setup:
1. Go to https://console.cloud.google.com/
2. Create a project and enable Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download credentials.json to config/gmail_credentials.json
5. First run will open browser for authentication

Usage:
    python -m src.watchers.gmail_watcher --vault ./AI_Employee_Vault

Or programmatically:
    from src.watchers import GmailWatcher
    watcher = GmailWatcher('./AI_Employee_Vault', './config/gmail_credentials.json')
    watcher.run()
"""

import os
import base64
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from email.utils import parsedate_to_datetime

from .base_watcher import BaseWatcher

# Gmail API imports - optional, graceful fallback if not installed
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False


# Gmail API scopes - read-only for safety
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailWatcher(BaseWatcher):
    """Watch Gmail for new important/unread emails."""

    def __init__(
        self,
        vault_path: str,
        credentials_path: str,
        token_path: Optional[str] = None,
        check_interval: int = 120,
        query: str = 'is:unread is:important',
        max_results: int = 10
    ):
        """
        Initialize Gmail Watcher.

        Args:
            vault_path: Path to the Obsidian vault
            credentials_path: Path to Gmail API credentials JSON
            token_path: Path to store OAuth token (defaults to config/gmail_token.json)
            check_interval: Seconds between checks (default 120)
            query: Gmail search query (default: unread important emails)
            max_results: Maximum emails to fetch per check
        """
        super().__init__(vault_path, check_interval, "GmailWatcher")

        if not GMAIL_API_AVAILABLE:
            raise ImportError(
                "Gmail API libraries not installed. Run:\n"
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path) if token_path else self.credentials_path.parent / 'gmail_token.json'
        self.query = query
        self.max_results = max_results
        self.processed_ids: set = set()
        self.service = None

        # Validate credentials file exists
        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"Gmail credentials not found at {self.credentials_path}\n"
                "Download from Google Cloud Console: https://console.cloud.google.com/"
            )

        # Initialize Gmail service
        self._initialize_service()

    def _initialize_service(self) -> None:
        """Initialize Gmail API service with OAuth."""
        creds = None

        # Load existing token
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            except Exception as e:
                self.logger.warning(f"Failed to load token: {e}")

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    self.logger.warning(f"Failed to refresh token: {e}")
                    creds = None

            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        self.service = build('gmail', 'v1', credentials=creds)
        self.logger.info("Gmail service initialized")

    def check_for_updates(self) -> List[Dict[str, Any]]:
        """Check for new unread important emails."""
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=self.query,
                maxResults=self.max_results
            ).execute()

            messages = results.get('messages', [])
            new_messages = []

            for msg in messages:
                if msg['id'] not in self.processed_ids:
                    try:
                        # Get full message details
                        full_msg = self.service.users().messages().get(
                            userId='me',
                            id=msg['id'],
                            format='full'
                        ).execute()
                        new_messages.append(full_msg)
                    except Exception as e:
                        self.logger.error(f"Error fetching message {msg['id']}: {e}")

            return new_messages

        except Exception as e:
            self.logger.error(f"Error checking Gmail: {e}")
            return []

    def create_action_file(self, item: Dict[str, Any]) -> Path:
        """Create action file for an email."""
        msg_id = item['id']
        headers = self._extract_headers(item)

        # Extract email details
        sender = headers.get('From', 'Unknown')
        subject = headers.get('Subject', 'No Subject')
        date = headers.get('Date', '')
        to = headers.get('To', '')
        cc = headers.get('Cc', '')

        # Parse date
        try:
            email_date = parsedate_to_datetime(date)
            formatted_date = email_date.strftime('%Y-%m-%d %H:%M:%S')
        except:
            formatted_date = date

        # Get email body
        body = self._extract_body(item)
        snippet = item.get('snippet', '')

        # Determine priority and category
        labels = item.get('labelIds', [])
        priority = self._determine_priority(labels, subject, sender)
        category = self._determine_category(labels, subject, body)

        # Check if requires approval based on content
        requires_approval = self._check_requires_approval(subject, body, sender)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        content = f'''---
type: email
message_id: "{msg_id}"
from: "{self._escape_yaml(sender)}"
to: "{self._escape_yaml(to)}"
subject: "{self._escape_yaml(subject)}"
date: "{formatted_date}"
received: "{datetime.now().isoformat()}"
priority: "{priority}"
category: "{category}"
status: pending
requires_approval: {str(requires_approval).lower()}
labels: [{', '.join(f'"{l}"' for l in labels)}]
---

# Email: {subject}

## Details

| Field | Value |
|-------|-------|
| **From** | {sender} |
| **To** | {to} |
| **CC** | {cc or 'None'} |
| **Date** | {formatted_date} |
| **Priority** | {priority} |
| **Category** | {category} |

## Preview

> {snippet}

## Full Body

{body[:2000]}{'...(truncated)' if len(body) > 2000 else ''}

## Suggested Actions

{self._get_suggested_actions(category, requires_approval)}

## Draft Response

<!-- Write your response here if needed -->

```
Subject: Re: {subject}

Dear {self._extract_name(sender)},

[Your response here]

Best regards,
[Your name]
```

## Notes

<!-- Add any notes here -->

'''
        # Create action file with safe filename
        safe_subject = self._sanitize_filename(subject[:40])
        action_filename = f'EMAIL_{timestamp}_{safe_subject}.md'
        action_path = self.needs_action / action_filename
        action_path.write_text(content, encoding='utf-8')

        # Mark as processed
        self.processed_ids.add(msg_id)

        return action_path

    def _extract_headers(self, message: Dict[str, Any]) -> Dict[str, str]:
        """Extract headers from message payload."""
        headers = {}
        payload = message.get('payload', {})

        for header in payload.get('headers', []):
            name = header.get('name', '')
            value = header.get('value', '')
            headers[name] = value

        return headers

    def _extract_body(self, message: Dict[str, Any]) -> str:
        """Extract email body from message payload."""
        payload = message.get('payload', {})

        # Try to get plain text body
        body = self._get_body_from_payload(payload)

        if not body:
            # Fallback to snippet
            body = message.get('snippet', '')

        return body

    def _get_body_from_payload(self, payload: Dict[str, Any]) -> str:
        """Recursively extract body from payload."""
        mime_type = payload.get('mimeType', '')

        # Direct body
        if 'body' in payload and 'data' in payload['body']:
            try:
                data = payload['body']['data']
                return base64.urlsafe_b64decode(data).decode('utf-8')
            except:
                pass

        # Multipart
        if 'parts' in payload:
            for part in payload['parts']:
                part_mime = part.get('mimeType', '')

                # Prefer plain text
                if part_mime == 'text/plain':
                    if 'body' in part and 'data' in part['body']:
                        try:
                            data = part['body']['data']
                            return base64.urlsafe_b64decode(data).decode('utf-8')
                        except:
                            pass

                # Recurse into nested parts
                if 'parts' in part:
                    body = self._get_body_from_payload(part)
                    if body:
                        return body

            # Fallback to HTML if no plain text
            for part in payload['parts']:
                if part.get('mimeType') == 'text/html':
                    if 'body' in part and 'data' in part['body']:
                        try:
                            data = part['body']['data']
                            html = base64.urlsafe_b64decode(data).decode('utf-8')
                            # Basic HTML stripping
                            return self._strip_html(html)
                        except:
                            pass

        return ''

    def _strip_html(self, html: str) -> str:
        """Basic HTML tag stripping."""
        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        # Remove HTML tags
        html = re.sub(r'<[^>]+>', ' ', html)
        # Clean up whitespace
        html = re.sub(r'\s+', ' ', html)
        return html.strip()

    def _determine_priority(self, labels: List[str], subject: str, sender: str) -> str:
        """Determine email priority."""
        subject_lower = subject.lower()
        sender_lower = sender.lower()

        # High priority indicators
        high_keywords = ['urgent', 'asap', 'important', 'action required', 'deadline', 'critical']
        if any(kw in subject_lower for kw in high_keywords):
            return 'high'

        if 'IMPORTANT' in labels:
            return 'high'

        if 'STARRED' in labels:
            return 'high'

        # Medium priority
        medium_keywords = ['follow up', 'reminder', 'update', 'review', 'feedback']
        if any(kw in subject_lower for kw in medium_keywords):
            return 'medium'

        return 'low'

    def _determine_category(self, labels: List[str], subject: str, body: str) -> str:
        """Categorize the email."""
        content = (subject + ' ' + body).lower()

        # Financial
        if any(word in content for word in ['invoice', 'payment', 'receipt', 'billing', 'transaction']):
            return 'financial'

        # Meeting/Calendar
        if any(word in content for word in ['meeting', 'calendar', 'schedule', 'appointment', 'call']):
            return 'meeting'

        # Support/Customer
        if any(word in content for word in ['support', 'help', 'issue', 'problem', 'complaint']):
            return 'support'

        # Marketing
        if 'CATEGORY_PROMOTIONS' in labels:
            return 'marketing'

        # Social
        if 'CATEGORY_SOCIAL' in labels:
            return 'social'

        return 'general'

    def _check_requires_approval(self, subject: str, body: str, sender: str) -> bool:
        """Check if email response requires human approval."""
        content = (subject + ' ' + body).lower()

        # Always require approval for these
        approval_keywords = [
            'contract', 'agreement', 'legal', 'confidential',
            'payment', 'invoice', 'wire transfer',
            'complaint', 'dispute', 'lawsuit',
            'termination', 'resignation'
        ]

        return any(kw in content for kw in approval_keywords)

    def _get_suggested_actions(self, category: str, requires_approval: bool) -> str:
        """Get suggested actions based on category."""
        base_actions = "- [ ] Review email content\n"

        if requires_approval:
            base_actions += "- [ ] **REQUIRES APPROVAL** - Move to Pending_Approval before responding\n"

        category_actions = {
            'financial': """- [ ] Verify payment/invoice details
- [ ] Check against records
- [ ] Process or flag for review
- [ ] Update accounting records if applicable""",
            'meeting': """- [ ] Check calendar availability
- [ ] Confirm or propose alternative time
- [ ] Add to calendar if confirmed
- [ ] Prepare meeting agenda if needed""",
            'support': """- [ ] Identify the issue
- [ ] Check knowledge base for solutions
- [ ] Draft helpful response
- [ ] Escalate if needed""",
            'marketing': """- [ ] Evaluate if relevant
- [ ] Unsubscribe if spam
- [ ] Archive if not actionable""",
            'general': """- [ ] Determine if response needed
- [ ] Draft appropriate response
- [ ] Archive after handling"""
        }

        return base_actions + category_actions.get(category, category_actions['general'])

    def _extract_name(self, sender: str) -> str:
        """Extract name from sender string."""
        # Format: "Name <email@example.com>" or just "email@example.com"
        match = re.match(r'^([^<]+)', sender)
        if match:
            name = match.group(1).strip()
            if name:
                return name.split()[0]  # First name only
        return 'there'

    def _sanitize_filename(self, text: str) -> str:
        """Create safe filename from text."""
        # Remove/replace unsafe characters
        safe = re.sub(r'[<>:"/\\|?*]', '', text)
        safe = re.sub(r'\s+', '_', safe)
        return safe.strip('_') or 'email'

    def _escape_yaml(self, text: str) -> str:
        """Escape text for YAML frontmatter."""
        return text.replace('"', '\\"').replace('\n', ' ')


# Standalone runner
if __name__ == '__main__':
    import argparse
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description='Gmail Watcher for AI Employee')
    parser.add_argument(
        '--vault',
        default='./AI_Employee_Vault',
        help='Path to Obsidian vault'
    )
    parser.add_argument(
        '--credentials',
        default='./config/gmail_credentials.json',
        help='Path to Gmail API credentials'
    )
    parser.add_argument(
        '--query',
        default='is:unread is:important',
        help='Gmail search query'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=120,
        help='Check interval in seconds'
    )

    args = parser.parse_args()

    try:
        watcher = GmailWatcher(
            vault_path=args.vault,
            credentials_path=args.credentials,
            query=args.query,
            check_interval=args.interval
        )

        print(f"Gmail Watcher started")
        print(f"Query: {args.query}")
        print(f"Check interval: {args.interval}s")
        print("Press Ctrl+C to stop...")

        watcher.run()

    except ImportError as e:
        print(f"Error: {e}")
        print("\nInstall Gmail dependencies with:")
        print("pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    except FileNotFoundError as e:
        print(f"Error: {e}")
