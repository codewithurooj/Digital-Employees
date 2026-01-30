"""
Email MCP Server - Send, draft, reply, and forward emails via Gmail API.

This MCP server provides email management capabilities for the AI Employee system.
All send operations require prior human approval through the HITL workflow.

Usage:
    from src.mcp_servers import EmailMCPServer

    server = EmailMCPServer(
        vault_path='./AI_Employee_Vault',
        credentials_path='./config/gmail_credentials.json'
    )

    # Send an approved email
    result = server.send_email(
        approval_id='appr_123',
        to=['client@example.com'],
        subject='Hello',
        body='Message content'
    )

Tools provided:
- send_email: Send an approved email
- draft_email: Create a draft email
- reply_email: Reply to an existing email
- forward_email: Forward an email
- list_drafts: List all draft emails
- delete_draft: Delete a draft
"""

import base64
import hashlib
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Gmail API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False

from ..cloud.work_zone import requires_local
from ..utils.hitl import ApprovalManager, ApprovalStatus
from ..utils.retry_handler import RateLimiter, retry, CircuitBreaker


# Gmail API scopes - need send permission
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Constants from design
MAX_RECIPIENTS = 100
MAX_SUBJECT_LENGTH = 500
MAX_BODY_LENGTH = 50000
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ATTACHMENTS = 10
MAX_DRAFTS = 100
EMAILS_PER_HOUR = 10


@dataclass
class Attachment:
    """Email attachment."""
    filename: str
    content_type: str
    data: str  # Base64 encoded

    def validate(self) -> List[str]:
        """Validate attachment and return list of errors."""
        errors = []

        if not self.filename or len(self.filename) > 255:
            errors.append("Filename must be 1-255 characters")

        if '/' in self.filename or '\\' in self.filename:
            errors.append("Filename cannot contain path separators")

        # Check size
        try:
            decoded = base64.b64decode(self.data)
            if len(decoded) > MAX_ATTACHMENT_SIZE:
                errors.append(f"Attachment exceeds {MAX_ATTACHMENT_SIZE // (1024*1024)}MB limit")
        except Exception:
            errors.append("Invalid base64 data")

        # Block dangerous extensions
        dangerous_ext = {'.exe', '.bat', '.cmd', '.ps1', '.sh', '.vbs', '.js'}
        ext = Path(self.filename).suffix.lower()
        if ext in dangerous_ext:
            errors.append(f"Blocked file type: {ext}")

        return errors

    @property
    def size_bytes(self) -> int:
        """Get decoded size in bytes."""
        try:
            return len(base64.b64decode(self.data))
        except:
            return 0


@dataclass
class EmailResult:
    """Result of an email operation."""
    success: bool
    message_id: Optional[str] = None
    thread_id: Optional[str] = None
    draft_id: Optional[str] = None
    status: str = ""
    error: Optional[str] = None
    error_type: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            'success': self.success,
            'status': self.status,
        }
        if self.message_id:
            result['message_id'] = self.message_id
        if self.thread_id:
            result['thread_id'] = self.thread_id
        if self.draft_id:
            result['draft_id'] = self.draft_id
        if self.error:
            result['error'] = self.error
            result['error_type'] = self.error_type
        result.update(self.details)
        return result


class EmailMCPServer:
    """
    Email MCP Server for the AI Employee system.

    Provides email operations with HITL approval integration,
    rate limiting, and comprehensive logging.
    """

    def __init__(
        self,
        vault_path: str,
        credentials_path: str,
        token_path: Optional[str] = None,
        known_recipients_file: Optional[str] = None,
        agent_zone=None,
    ):
        """
        Initialize Email MCP Server.

        Args:
            vault_path: Path to the Obsidian vault
            credentials_path: Path to Gmail API credentials
            token_path: Path to store OAuth token
            known_recipients_file: Path to known recipients whitelist
            agent_zone: WorkZone enum value for work-zone enforcement
        """
        self.agent_zone = agent_zone
        if not GMAIL_API_AVAILABLE:
            raise ImportError(
                "Gmail API libraries not installed. Run:\n"
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
            )

        self.vault_path = Path(vault_path)
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path) if token_path else self.credentials_path.parent / 'gmail_token.json'
        self.logs_path = self.vault_path / 'Logs'
        self.logs_path.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.approval_manager = ApprovalManager(str(self.vault_path))
        self.rate_limiter = RateLimiter('email_mcp', max_calls=EMAILS_PER_HOUR, period_seconds=3600)
        self.circuit_breaker = CircuitBreaker('gmail_api', failure_threshold=5)

        # Known recipients whitelist
        self.known_recipients: set = set()
        if known_recipients_file and Path(known_recipients_file).exists():
            self._load_known_recipients(known_recipients_file)

        # Gmail service
        self.service = None
        self._initialize_service()

        self.logger = logging.getLogger('EmailMCPServer')

    def _initialize_service(self) -> None:
        """Initialize Gmail API service."""
        creds = None

        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            except Exception as e:
                self.logger.warning(f"Failed to load token: {e}")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None

            if not creds:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(f"Gmail credentials not found: {self.credentials_path}")

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        self.service = build('gmail', 'v1', credentials=creds)
        self.logger.info("Gmail service initialized")

    def _load_known_recipients(self, filepath: str) -> None:
        """Load known recipients from file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                self.known_recipients = set(data.get('recipients', []))
            self.logger.info(f"Loaded {len(self.known_recipients)} known recipients")
        except Exception as e:
            self.logger.warning(f"Failed to load known recipients: {e}")

    def _save_known_recipients(self, filepath: str) -> None:
        """Save known recipients to file."""
        with open(filepath, 'w') as f:
            json.dump({'recipients': list(self.known_recipients)}, f, indent=2)

    def _validate_email(self, email: str) -> bool:
        """Validate email address format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _validate_approval(
        self,
        approval_id: str,
        expected_action: str,
        content_hash: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate an approval ID.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check approval exists and is approved
        # In a real implementation, we'd check a database
        # For now, check if file exists in Approved folder
        approved_files = list((self.vault_path / 'Approved').glob(f'*{approval_id}*'))

        if not approved_files:
            return False, "Approval ID not found or not yet approved"

        # Read approval file to verify details
        approval_file = approved_files[0]
        content = approval_file.read_text()

        if 'status: consumed' in content.lower():
            return False, "Approval has already been used"

        # TODO: Check expiration, content hash, etc.

        return True, None

    def _consume_approval(self, approval_id: str) -> None:
        """Mark an approval as consumed."""
        approved_files = list((self.vault_path / 'Approved').glob(f'*{approval_id}*'))
        if approved_files:
            filepath = approved_files[0]
            content = filepath.read_text()
            content = content.replace('status: pending', 'status: consumed')
            content += f"\n\n---\n*Consumed at: {datetime.now().isoformat()}*\n"
            filepath.write_text(content)

    def _check_unknown_recipients(self, recipients: List[str]) -> List[str]:
        """Check for unknown recipients."""
        unknown = []
        for email in recipients:
            if email.lower() not in self.known_recipients:
                unknown.append(email)
        return unknown

    def _add_known_recipient(self, email: str) -> None:
        """Add a recipient to known list after successful send."""
        self.known_recipients.add(email.lower())

    def _create_message(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        body_type: str = 'plain',
        attachments: Optional[List[Attachment]] = None,
        thread_id: Optional[str] = None,
        in_reply_to: Optional[str] = None
    ) -> dict:
        """Create a Gmail API message object."""
        if attachments:
            message = MIMEMultipart()
            message.attach(MIMEText(body, body_type))

            for attachment in attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(base64.b64decode(attachment.data))
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment.filename}"'
                )
                message.attach(part)
        else:
            message = MIMEText(body, body_type)

        message['To'] = ', '.join(to)
        message['Subject'] = subject

        if cc:
            message['Cc'] = ', '.join(cc)

        if in_reply_to:
            message['In-Reply-To'] = in_reply_to
            message['References'] = in_reply_to

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        msg_body = {'raw': raw}
        if thread_id:
            msg_body['threadId'] = thread_id

        return msg_body

    def _log_operation(self, operation: str, details: Dict[str, Any]) -> None:
        """Log an operation to the daily log file."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        entry = {
            'timestamp': datetime.now().isoformat(),
            'component': 'EmailMCPServer',
            'operation': operation,
            'details': details
        }

        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text())
            except:
                logs = []

        logs.append(entry)
        log_file.write_text(json.dumps(logs, indent=2), encoding='utf-8')

    # =========================================================================
    # MCP Tools
    # =========================================================================

    @requires_local
    def send_email(
        self,
        approval_id: str,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        body_type: str = 'plain',
        attachments: Optional[List[Dict[str, str]]] = None,
        thread_id: Optional[str] = None
    ) -> EmailResult:
        """
        Send an approved email.

        Args:
            approval_id: Approval ID from HITL workflow
            to: Primary recipients
            subject: Email subject
            body: Email body
            cc: CC recipients
            bcc: BCC recipients
            body_type: 'plain' or 'html'
            attachments: List of attachment dicts with filename, content_type, data
            thread_id: Thread ID for conversation

        Returns:
            EmailResult with operation status
        """
        # Validate approval
        valid, error = self._validate_approval(approval_id, 'send_email')
        if not valid:
            return EmailResult(
                success=False,
                status='failed',
                error=error,
                error_type='ApprovalError'
            )

        # Rate limit check
        if not self.rate_limiter.allow():
            return EmailResult(
                success=False,
                status='failed',
                error=f'Rate limit exceeded. {self.rate_limiter.remaining()} of {EMAILS_PER_HOUR} remaining.',
                error_type='RateLimitError',
                details={'reset_at': datetime.now().isoformat()}
            )

        # Validate recipients
        all_recipients = to + (cc or []) + (bcc or [])
        if len(all_recipients) > MAX_RECIPIENTS:
            return EmailResult(
                success=False,
                status='failed',
                error=f'Too many recipients. Max {MAX_RECIPIENTS}.',
                error_type='ValidationError'
            )

        for email in all_recipients:
            if not self._validate_email(email):
                return EmailResult(
                    success=False,
                    status='failed',
                    error=f'Invalid email address: {email}',
                    error_type='ValidationError'
                )

        # Check for unknown recipients
        unknown = self._check_unknown_recipients(all_recipients)
        if unknown:
            return EmailResult(
                success=False,
                status='failed',
                error=f'Unknown recipients: {", ".join(unknown)}',
                error_type='UnknownRecipientError',
                details={'unknown_recipients': unknown}
            )

        # Validate subject and body
        if not subject or len(subject) > MAX_SUBJECT_LENGTH:
            return EmailResult(
                success=False,
                status='failed',
                error=f'Subject must be 1-{MAX_SUBJECT_LENGTH} characters',
                error_type='ValidationError'
            )

        if not body or len(body) > MAX_BODY_LENGTH:
            return EmailResult(
                success=False,
                status='failed',
                error=f'Body must be 1-{MAX_BODY_LENGTH} characters',
                error_type='ValidationError'
            )

        # Validate attachments
        attachment_objects = []
        if attachments:
            if len(attachments) > MAX_ATTACHMENTS:
                return EmailResult(
                    success=False,
                    status='failed',
                    error=f'Too many attachments. Max {MAX_ATTACHMENTS}.',
                    error_type='AttachmentError'
                )

            total_size = 0
            for att_dict in attachments:
                att = Attachment(**att_dict)
                errors = att.validate()
                if errors:
                    return EmailResult(
                        success=False,
                        status='failed',
                        error='; '.join(errors),
                        error_type='AttachmentError'
                    )
                total_size += att.size_bytes
                attachment_objects.append(att)

            if total_size > MAX_ATTACHMENT_SIZE:
                return EmailResult(
                    success=False,
                    status='failed',
                    error=f'Total attachment size exceeds {MAX_ATTACHMENT_SIZE // (1024*1024)}MB',
                    error_type='AttachmentError'
                )

        # Create and send message
        try:
            message = self._create_message(
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc,
                body_type=body_type,
                attachments=attachment_objects,
                thread_id=thread_id
            )

            result = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()

            # Consume approval
            self._consume_approval(approval_id)

            # Add recipients to known list
            for email in all_recipients:
                self._add_known_recipient(email)

            # Log success
            self._log_operation('send_email', {
                'message_id': result['id'],
                'thread_id': result.get('threadId'),
                'recipients': len(all_recipients),
                'approval_id': approval_id
            })

            return EmailResult(
                success=True,
                message_id=result['id'],
                thread_id=result.get('threadId'),
                status='sent',
                details={
                    'sent_at': datetime.now().isoformat(),
                    'recipients_count': len(all_recipients),
                    'approval_id': approval_id
                }
            )

        except HttpError as e:
            self._log_operation('send_email_error', {
                'error': str(e),
                'approval_id': approval_id
            })
            return EmailResult(
                success=False,
                status='failed',
                error=f'Gmail API error: {str(e)}',
                error_type='GmailAPIError'
            )

    def draft_email(
        self,
        to: Optional[List[str]] = None,
        subject: Optional[str] = None,
        body: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        body_type: str = 'plain',
        attachments: Optional[List[Dict[str, str]]] = None,
        thread_id: Optional[str] = None
    ) -> EmailResult:
        """
        Create a draft email (no approval required).

        Args:
            to: Primary recipients (optional for drafts)
            subject: Email subject
            body: Email body
            cc: CC recipients
            bcc: BCC recipients
            body_type: 'plain' or 'html'
            attachments: List of attachment dicts
            thread_id: Thread ID for reply context

        Returns:
            EmailResult with draft_id
        """
        warnings = []

        if not to:
            warnings.append("No recipients specified - add before sending")
        if not subject:
            warnings.append("No subject line - consider adding before sending")

        # Validate email addresses if provided
        all_recipients = (to or []) + (cc or []) + (bcc or [])
        for email in all_recipients:
            if not self._validate_email(email):
                return EmailResult(
                    success=False,
                    status='failed',
                    error=f'Invalid email address: {email}',
                    error_type='ValidationError'
                )

        # Validate attachments if provided
        attachment_objects = []
        if attachments:
            total_size = 0
            for att_dict in attachments:
                att = Attachment(**att_dict)
                errors = att.validate()
                if errors:
                    return EmailResult(
                        success=False,
                        status='failed',
                        error='; '.join(errors),
                        error_type='AttachmentError'
                    )
                total_size += att.size_bytes
                attachment_objects.append(att)

            if total_size > MAX_ATTACHMENT_SIZE:
                return EmailResult(
                    success=False,
                    status='failed',
                    error=f'Total attachment size exceeds {MAX_ATTACHMENT_SIZE // (1024*1024)}MB',
                    error_type='AttachmentError'
                )

        try:
            message = self._create_message(
                to=to or [],
                subject=subject or '',
                body=body or '',
                cc=cc,
                bcc=bcc,
                body_type=body_type,
                attachments=attachment_objects,
                thread_id=thread_id
            )

            draft = self.service.users().drafts().create(
                userId='me',
                body={'message': message}
            ).execute()

            self._log_operation('draft_email', {
                'draft_id': draft['id'],
                'has_recipients': bool(to),
                'has_subject': bool(subject)
            })

            return EmailResult(
                success=True,
                draft_id=draft['id'],
                thread_id=thread_id,
                status='created',
                details={
                    'created_at': datetime.now().isoformat(),
                    'validation_warnings': warnings
                }
            )

        except HttpError as e:
            return EmailResult(
                success=False,
                status='failed',
                error=f'Gmail API error: {str(e)}',
                error_type='GmailAPIError'
            )

    @requires_local
    def reply_email(
        self,
        approval_id: str,
        message_id: str,
        body: str,
        body_type: str = 'plain',
        reply_all: bool = False,
        additional_cc: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, str]]] = None,
        include_quoted_text: bool = True
    ) -> EmailResult:
        """
        Reply to an existing email (requires approval).

        Args:
            approval_id: Approval ID from HITL workflow
            message_id: Gmail message ID to reply to
            body: Reply body
            body_type: 'plain' or 'html'
            reply_all: Reply to all recipients
            additional_cc: Additional CC recipients
            attachments: Attachments to include
            include_quoted_text: Include original email in reply

        Returns:
            EmailResult with operation status
        """
        # Validate approval
        valid, error = self._validate_approval(approval_id, 'reply_email')
        if not valid:
            return EmailResult(
                success=False,
                status='failed',
                error=error,
                error_type='ApprovalError'
            )

        # Rate limit check
        if not self.rate_limiter.allow():
            return EmailResult(
                success=False,
                status='failed',
                error='Rate limit exceeded',
                error_type='RateLimitError'
            )

        try:
            # Get original message
            original = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Extract headers
            headers = {h['name']: h['value'] for h in original['payload']['headers']}
            thread_id = original.get('threadId')

            # Determine recipients
            to = [headers.get('From', '')]
            cc = []

            if reply_all:
                # Add original To and CC
                if 'To' in headers:
                    to.extend([e.strip() for e in headers['To'].split(',')])
                if 'Cc' in headers:
                    cc.extend([e.strip() for e in headers['Cc'].split(',')])

            if additional_cc:
                cc.extend(additional_cc)

            # Remove duplicates and self
            to = list(set(to))
            cc = list(set(cc) - set(to))

            # Build reply body
            reply_body = body
            if include_quoted_text:
                reply_body += f"\n\n--- Original Message ---\n{original.get('snippet', '')}"

            # Create and send
            message = self._create_message(
                to=to,
                subject=f"Re: {headers.get('Subject', '')}",
                body=reply_body,
                cc=cc,
                body_type=body_type,
                thread_id=thread_id,
                in_reply_to=message_id
            )

            result = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()

            self._consume_approval(approval_id)

            self._log_operation('reply_email', {
                'message_id': result['id'],
                'in_reply_to': message_id,
                'thread_id': thread_id,
                'approval_id': approval_id
            })

            return EmailResult(
                success=True,
                message_id=result['id'],
                thread_id=thread_id,
                status='sent',
                details={
                    'sent_at': datetime.now().isoformat(),
                    'in_reply_to': message_id,
                    'recipients_count': len(to) + len(cc),
                    'approval_id': approval_id
                }
            )

        except HttpError as e:
            return EmailResult(
                success=False,
                status='failed',
                error=f'Gmail API error: {str(e)}',
                error_type='GmailAPIError'
            )

    @requires_local
    def forward_email(
        self,
        approval_id: str,
        message_id: str,
        to: List[str],
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        added_message: Optional[str] = None,
        include_attachments: bool = True
    ) -> EmailResult:
        """
        Forward an email to new recipients (requires approval).

        Args:
            approval_id: Approval ID from HITL workflow
            message_id: Gmail message ID to forward
            to: Forward recipients
            cc: CC recipients
            bcc: BCC recipients
            added_message: Message to prepend
            include_attachments: Include original attachments

        Returns:
            EmailResult with operation status
        """
        # Validate approval
        valid, error = self._validate_approval(approval_id, 'forward_email')
        if not valid:
            return EmailResult(
                success=False,
                status='failed',
                error=error,
                error_type='ApprovalError'
            )

        # Rate limit check
        if not self.rate_limiter.allow():
            return EmailResult(
                success=False,
                status='failed',
                error='Rate limit exceeded',
                error_type='RateLimitError'
            )

        # Check unknown recipients
        all_recipients = to + (cc or []) + (bcc or [])
        unknown = self._check_unknown_recipients(all_recipients)
        if unknown:
            return EmailResult(
                success=False,
                status='failed',
                error=f'Unknown recipients: {", ".join(unknown)}',
                error_type='UnknownRecipientError'
            )

        try:
            # Get original message
            original = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            headers = {h['name']: h['value'] for h in original['payload']['headers']}

            # Build forward body
            forward_body = ""
            if added_message:
                forward_body = added_message + "\n\n"

            forward_body += f"---------- Forwarded message ----------\n"
            forward_body += f"From: {headers.get('From', 'Unknown')}\n"
            forward_body += f"Date: {headers.get('Date', '')}\n"
            forward_body += f"Subject: {headers.get('Subject', '')}\n"
            forward_body += f"To: {headers.get('To', '')}\n\n"
            forward_body += original.get('snippet', '')

            # Create and send
            message = self._create_message(
                to=to,
                subject=f"Fwd: {headers.get('Subject', '')}",
                body=forward_body,
                cc=cc,
                bcc=bcc
            )

            result = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()

            self._consume_approval(approval_id)

            for email in all_recipients:
                self._add_known_recipient(email)

            self._log_operation('forward_email', {
                'message_id': result['id'],
                'forwarded_from': message_id,
                'approval_id': approval_id
            })

            return EmailResult(
                success=True,
                message_id=result['id'],
                thread_id=result.get('threadId'),
                status='sent',
                details={
                    'sent_at': datetime.now().isoformat(),
                    'forwarded_from': message_id,
                    'recipients_count': len(all_recipients),
                    'approval_id': approval_id
                }
            )

        except HttpError as e:
            return EmailResult(
                success=False,
                status='failed',
                error=f'Gmail API error: {str(e)}',
                error_type='GmailAPIError'
            )

    def list_drafts(
        self,
        limit: int = 20,
        offset: int = 0
    ) -> EmailResult:
        """
        List all draft emails.

        Args:
            limit: Maximum drafts to return (1-100)
            offset: Number to skip for pagination

        Returns:
            EmailResult with drafts list
        """
        limit = max(1, min(100, limit))

        try:
            results = self.service.users().drafts().list(
                userId='me',
                maxResults=limit
            ).execute()

            drafts = results.get('drafts', [])

            draft_list = []
            for draft in drafts[offset:offset + limit]:
                # Get draft details
                full_draft = self.service.users().drafts().get(
                    userId='me',
                    id=draft['id']
                ).execute()

                msg = full_draft.get('message', {})
                headers = {}
                if 'payload' in msg:
                    headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}

                draft_list.append({
                    'draft_id': draft['id'],
                    'subject': headers.get('Subject'),
                    'to': headers.get('To', '').split(', ') if headers.get('To') else [],
                    'snippet': msg.get('snippet', '')[:100],
                    'thread_id': msg.get('threadId')
                })

            return EmailResult(
                success=True,
                status='success',
                details={
                    'drafts': draft_list,
                    'total_count': len(drafts),
                    'limit': limit,
                    'offset': offset,
                    'has_more': len(drafts) > offset + limit
                }
            )

        except HttpError as e:
            return EmailResult(
                success=False,
                status='failed',
                error=f'Gmail API error: {str(e)}',
                error_type='GmailAPIError'
            )

    def delete_draft(self, draft_id: str) -> EmailResult:
        """
        Delete a draft email.

        Args:
            draft_id: Gmail draft ID to delete

        Returns:
            EmailResult with operation status
        """
        try:
            self.service.users().drafts().delete(
                userId='me',
                id=draft_id
            ).execute()

            self._log_operation('delete_draft', {'draft_id': draft_id})

            return EmailResult(
                success=True,
                draft_id=draft_id,
                status='deleted',
                details={'deleted_at': datetime.now().isoformat()}
            )

        except HttpError as e:
            # If already deleted, return success (idempotent)
            if 'Not Found' in str(e):
                return EmailResult(
                    success=True,
                    draft_id=draft_id,
                    status='deleted',
                    details={'note': 'Draft was already deleted or does not exist'}
                )

            return EmailResult(
                success=False,
                status='failed',
                error=f'Gmail API error: {str(e)}',
                error_type='GmailAPIError'
            )

    def get_status(self) -> Dict[str, Any]:
        """Get current server status."""
        return {
            'server': 'EmailMCPServer',
            'rate_limit': self.rate_limiter.get_status(),
            'circuit_breaker': self.circuit_breaker.get_status(),
            'known_recipients': len(self.known_recipients)
        }
