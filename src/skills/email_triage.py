"""Email Triage Skill - Categorize and draft responses for incoming emails.

Cloud agent uses this to triage emails and create draft responses
in Pending_Approval/email/ for the local agent to review and send.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

URGENT_KEYWORDS = [
    "urgent", "asap", "emergency", "critical", "immediately",
    "server down", "production", "outage", "deadline today",
    "action required", "time sensitive",
]

LOW_PRIORITY_KEYWORDS = [
    "newsletter", "unsubscribe", "promotional", "no-reply", "noreply",
    "weekly update", "digest", "marketing", "subscription",
]


class EmailTriageSkill:
    """Skill for triaging incoming emails."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.pending_email_path = self.vault_path / "Pending_Approval" / "email"
        self.updates_path = self.vault_path / "Updates"
        self.logs_path = self.vault_path / "Logs"

        self.pending_email_path.mkdir(parents=True, exist_ok=True)
        self.updates_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)

    def categorize_email(self, email_data: dict[str, Any]) -> dict[str, Any]:
        """Categorize email into priority level.

        Args:
            email_data: Dict with from, subject, body, date keys

        Returns:
            Dict with priority (urgent/normal/low), reason
        """
        subject = (email_data.get("subject") or "").lower()
        body = (email_data.get("body") or "").lower()
        sender = (email_data.get("from") or "").lower()
        combined = f"{subject} {body} {sender}"

        for keyword in URGENT_KEYWORDS:
            if keyword in combined:
                return {
                    "priority": "urgent",
                    "reason": f"Contains urgent keyword: '{keyword}'",
                }

        for keyword in LOW_PRIORITY_KEYWORDS:
            if keyword in combined:
                return {
                    "priority": "low",
                    "reason": f"Contains low-priority keyword: '{keyword}'",
                }

        return {
            "priority": "normal",
            "reason": "No priority keywords detected",
        }

    def triage_email(self, email_data: dict[str, Any]) -> dict[str, Any]:
        """Full triage: categorize and create draft response file.

        Args:
            email_data: Dict with from, subject, body, date, message_id

        Returns:
            Dict with success, priority, draft_path
        """
        category = self.categorize_email(email_data)
        priority = category["priority"]

        message_id = email_data.get("message_id", "unknown")
        sender = email_data.get("from", "unknown")
        subject = email_data.get("subject", "No Subject")
        body = email_data.get("body", "")
        date = email_data.get("date", datetime.now().isoformat())

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"email_triage_{timestamp}_{message_id}.md"

        draft_content = f"""---
type: email_triage
priority: {priority}
from: "{sender}"
subject: "{subject}"
message_id: "{message_id}"
triaged_at: {datetime.now().isoformat()}
source_agent: cloud
requires_local_action: true
---

# Email Triage: {subject}

## Priority: {priority.upper()}

**From**: {sender}
**Date**: {date}
**Reason**: {category["reason"]}

## Original Message

{body}

## Suggested Response

> Draft a response acknowledging receipt and addressing the sender's request.

## Action Required

- [ ] Review triaged email
- [ ] Approve or edit draft response
- [ ] Send via local agent

---
*Triaged by Cloud Agent at {datetime.now().isoformat()}*
"""

        draft_path = self.pending_email_path / filename
        draft_path.write_text(draft_content, encoding="utf-8")

        self._log_action("email_triage", {
            "message_id": message_id,
            "from": sender,
            "subject": subject,
            "priority": priority,
            "draft_path": str(draft_path),
        })

        return {
            "success": True,
            "priority": priority,
            "reason": category["reason"],
            "draft_path": str(draft_path),
        }

    def generate_summary(self, emails: list[dict[str, Any]]) -> str:
        """Generate a summary of triaged emails.

        Args:
            emails: List of email data dicts

        Returns:
            Markdown summary string
        """
        urgent = []
        normal = []
        low = []

        for email in emails:
            category = self.categorize_email(email)
            entry = {
                "from": email.get("from", "unknown"),
                "subject": email.get("subject", "No Subject"),
                "priority": category["priority"],
            }
            if category["priority"] == "urgent":
                urgent.append(entry)
            elif category["priority"] == "low":
                low.append(entry)
            else:
                normal.append(entry)

        timestamp = datetime.now().isoformat()
        summary = f"""---
type: email_summary
generated_at: {timestamp}
total_emails: {len(emails)}
urgent_count: {len(urgent)}
normal_count: {len(normal)}
low_count: {len(low)}
---

# Email Summary

> Generated at {timestamp}

## Overview

- **Total**: {len(emails)} emails
- **Urgent**: {len(urgent)}
- **Normal**: {len(normal)}
- **Low Priority**: {len(low)}

"""

        if urgent:
            summary += "## Urgent Emails\n\n"
            for e in urgent:
                summary += f"- **{e['subject']}** from {e['from']}\n"
            summary += "\n"

        if normal:
            summary += "## Normal Priority\n\n"
            for e in normal:
                summary += f"- **{e['subject']}** from {e['from']}\n"
            summary += "\n"

        if low:
            summary += "## Low Priority\n\n"
            for e in low:
                summary += f"- **{e['subject']}** from {e['from']}\n"
            summary += "\n"

        summary += "---\n*Auto-generated by Email Triage Skill*\n"

        summary_path = self.updates_path / "email_summary.md"
        summary_path.write_text(summary, encoding="utf-8")

        return summary

    def _log_action(self, action: str, details: dict[str, Any]) -> None:
        """Log action to daily log file."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_path / f"{today}.jsonl"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "component": "email_triage",
            "action": action,
            "details": details,
        }

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
