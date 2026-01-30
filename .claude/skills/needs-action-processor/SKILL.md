---
name: needs-action-processor
description: Process files in the Needs_Action folder according to Company Handbook rules. Use this skill when you need to handle tasks placed in the Needs_Action directory by watchers, following the rules defined in the Company Handbook.
---

# Needs Action Processor

Process files in the Needs_Action folder according to Company Handbook rules. Use this skill when you need to handle tasks placed in the Needs_Action directory by watchers, following the rules defined in the Company Handbook.

## When to Use This Skill

Use this skill when:
- There are files in the Needs_Action folder that need processing
- You need to apply Company Handbook rules to incoming tasks
- Watchers have placed files in Needs_Action that require action

## How to Use This Skill

1. Check the Needs_Action folder for pending files
2. Read the Company Handbook rules
3. Process each file according to the rules
4. Update the Dashboard with outcomes
5. Move processed files to appropriate folders

## Files and Directories

- `<vault>/Needs_Action/` - Contains files waiting for processing
- `<vault>/Company_Handbook.md` - Rules for processing tasks
- `<vault>/Dashboard.md` - Log of completed actions
- `<vault>/Done/` - Successfully processed files
- `<vault>/Pending_Approval/` - Files awaiting approval

## Company Handbook Rule Processing

The script analyzes each file and applies rules based on the Company Handbook:

- **Financial Guidelines**: Payments over $100 require approval - moves to Pending_Approval
- **Communication Guidelines**: Professional and courteous communications
- **Task Management**: Prioritize urgent items marked with 'urgent', 'asap', 'emergency', etc.
- **Custom Rules**: Any specific rules defined in your Company Handbook

The processing logic will:
1. Read the Company Handbook from `<vault>/Company_Handbook.md`
2. Parse rules based on headers like "Financial Guidelines", "Communication Guidelines", etc.
3. Apply relevant rules based on content analysis
4. Take appropriate actions (move to Done, Pending Approval, etc.)
5. Log decisions in the Dashboard for transparency

## Processing Workflow

For each file in Needs_Action:

1. **Analyze**: Read the file content and identify the type of task
2. **Apply Rules**: Consult Company Handbook for appropriate action
3. **Execute**: Perform required action using available tools
4. **Update**: Log the action in Dashboard and move the file

## Available Commands

- `process_needs_action_files()` - Process all files in Needs_Action
- `scan_needs_action_folder()` - Scan for pending files only
