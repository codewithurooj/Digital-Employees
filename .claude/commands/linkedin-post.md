# LinkedIn Post Skill

Create, draft, and manage LinkedIn posts with HITL approval integration.

## Usage

```
/linkedin-post [action] [options]
```

## Actions

### Draft a Post
Create a new post draft that will be submitted for approval.

```
/linkedin-post draft "Your post content here" --visibility public
```

Options:
- `--visibility`: `public` (default) or `connections`
- `--type`: `text` (default), `article`, `poll`
- `--schedule`: ISO datetime for scheduled posting (e.g., `2026-01-21T09:00:00`)
- `--hashtags`: Additional hashtags (auto-extracted from content too)
- `--url`: Article URL (for article posts)

### List Drafts
View all draft posts and their status.

```
/linkedin-post list [--status pending_approval|draft|published]
```

### Publish Approved Post
Publish a post that has been approved through HITL workflow.

```
/linkedin-post publish <approval_id>
```

### Delete Draft
Delete a draft post (cannot delete published posts).

```
/linkedin-post delete <draft_id>
```

### Check Status
View rate limits, circuit breaker status, and draft counts.

```
/linkedin-post status
```

## Workflow

1. **Draft Creation**: User creates a draft via `/linkedin-post draft`
2. **Approval Request**: System creates approval request in `Pending_Approval/`
3. **Human Review**: Human reviews and moves to `Approved/` or `Rejected/`
4. **Publishing**: Once approved, use `/linkedin-post publish <approval_id>`

## Rate Limits

Per Company Handbook:
- Maximum 3 posts per day
- Posts require human approval before publishing
- Circuit breaker activates after 3 consecutive failures

## Examples

### Simple Text Post
```
/linkedin-post draft "Excited to share that our team just shipped a major feature! Great work everyone. #teamwork #shipping"
```

### Scheduled Post
```
/linkedin-post draft "Monday motivation: Start the week with intention." --schedule 2026-01-21T08:00:00
```

### Article Share
```
/linkedin-post draft "Great insights on AI in healthcare:" --type article --url https://example.com/article
```

### Poll
```
/linkedin-post draft "What's your biggest challenge with remote work?" --type poll --poll-question "Biggest remote work challenge?" --poll-options "Communication" "Work-life balance" "Collaboration" "Staying motivated"
```

## Action File Format

When a draft is created, an action file is generated in `Needs_Action/`:

```markdown
---
type: linkedin_post
draft_id: "draft_20260120_123456_abc12345"
approval_id: "linkedin_post_20260120_123456"
post_type: "text"
visibility: "public"
status: pending_approval
requires_approval: true
---

# LinkedIn Post Draft

## Post Preview

[Post content here]

## Approval Checklist

- [ ] Content is professional and appropriate
- [ ] No confidential information disclosed
- [ ] Hashtags are relevant
- [ ] Timing is appropriate
```

## Integration

The skill integrates with:
- **HITL Approval System**: All posts require approval before publishing
- **Rate Limiter**: Enforces 3 posts/day limit
- **Circuit Breaker**: Protects against LinkedIn API issues
- **Logging**: All operations logged to `Logs/`

## Implementation

```python
from src.skills import LinkedInPostingSkill

skill = LinkedInPostingSkill(
    vault_path='./AI_Employee_Vault',
    session_path='./config/linkedin_session'
)

# Create draft
result = skill.draft_post(
    content="Your post content",
    visibility="public"
)

# After approval, publish
result = skill.publish_approved_post(approval_id)
```
