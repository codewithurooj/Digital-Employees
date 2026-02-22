---
type: approval_request
action: send_email
to: "client@example.com"
subject: "Re: Project Update - January 2026"
created: "2026-02-22T11:00:00Z"
expires: "2026-02-23T11:00:00Z"
status: pending
requires_approval: true
source_file: "EMAIL_20260222_project_update.md"
priority: high
---

# Approval Required: Send Email

## Action Details

| Field | Value |
|-------|-------|
| **Action** | Send Email |
| **To** | client@example.com |
| **Subject** | Re: Project Update - January 2026 |
| **Priority** | High |
| **Created** | 2026-02-22 11:00:00 |
| **Expires** | 2026-02-23 11:00:00 |

## Email Body

```
Dear Client,

Thank you for reaching out regarding the project update.

I wanted to confirm that Phase 2 of the project is on track and
we expect to deliver the milestone by March 1st, 2026.

Please let me know if you have any questions.

Best regards,
Your AI Employee
```

## Why Approval Is Required

- Outgoing email to external contact
- Contains project timeline commitments
- New recipient not in approved contacts list

## To Approve

Move this file to `/Approved` folder.

## To Reject

Move this file to `/Rejected` folder.
