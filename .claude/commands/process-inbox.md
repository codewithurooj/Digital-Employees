# Process Inbox Skill

Process all items in the Needs_Action folder and create appropriate plans.

## Purpose

This skill processes pending action items created by watchers and determines the appropriate response based on the Company Handbook rules.

## Instructions

### Step 1: Gather Context

1. Read `AI_Employee_Vault/Company_Handbook.md` to understand operational rules
2. Read `AI_Employee_Vault/Business_Goals.md` to understand priorities
3. Read `AI_Employee_Vault/Dashboard.md` to understand current status

### Step 2: Process Each Item

For each `.md` file in `AI_Employee_Vault/Needs_Action/`:

1. **Read the file** and extract:
   - Type (from frontmatter: file_drop, email, whatsapp, etc.)
   - Priority (high, medium, low)
   - Status (should be "pending")
   - Key details

2. **Analyze against rules**:
   - Does this require human approval? (Check Company_Handbook.md thresholds)
   - What actions are needed?
   - What is the urgency?

3. **Create a Plan**:
   - Write a plan file to `AI_Employee_Vault/Plans/`
   - Include clear action steps
   - Reference relevant handbook rules

4. **Route appropriately**:
   - If requires approval → Move to `Pending_Approval/`
   - If can auto-process → Execute and move to `Done/`
   - If needs more info → Flag for human review

### Step 3: Update Dashboard

Update `AI_Employee_Vault/Dashboard.md` with:
- Number of items processed
- Items pending approval
- Any urgent items flagged

## Output Format

### Plan File Template

Create in `AI_Employee_Vault/Plans/PLAN_{timestamp}_{type}.md`:

```markdown
---
type: plan
source_file: "{original_action_file}"
created: "{ISO_timestamp}"
priority: "{priority}"
requires_approval: {true|false}
status: pending
---

# Plan: {Brief Description}

## Source Item
- **File**: {source_file_name}
- **Type**: {item_type}
- **Received**: {timestamp}

## Analysis

{Your analysis of the item and what needs to be done}

## Proposed Actions

1. [ ] {Action 1}
2. [ ] {Action 2}
3. [ ] {Action 3}

## Handbook Rules Applied

- {Rule 1 reference}
- {Rule 2 reference}

## Approval Required

{Yes/No and reason}

## Notes

{Any additional context}
```

## Rules to Follow

1. **Always follow Company_Handbook.md rules** - These are non-negotiable
2. **Never auto-approve**:
   - Payments > $100
   - Communications to new contacts
   - Any action marked "requires_approval" in source
3. **Always log actions** - Every decision must be traceable
4. **When uncertain, ask** - Flag for human review rather than guessing
5. **Prioritize correctly**:
   - P0 (Critical): Process immediately
   - P1 (High): Process same session
   - P2 (Medium): Queue for processing
   - P3 (Low): Process when time permits

## Example Usage

```
User: Process my inbox
Claude: I'll process all pending items in your Needs_Action folder.

[Reads Company_Handbook.md]
[Reads each file in Needs_Action/]
[Creates plans in Plans/]
[Updates Dashboard.md]

Summary:
- Processed: 5 items
- Plans created: 5
- Pending approval: 2
- Auto-processed: 3
```

## Error Handling

- If a file cannot be parsed, log error and skip
- If handbook rules are ambiguous, flag for human review
- If vault folders don't exist, create them
- Never delete source files until action is complete
