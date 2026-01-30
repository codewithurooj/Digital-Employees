"""
Process Inbox Skill - Processes all items in Needs_Action folder.

This skill uses the Ralph Wiggum Loop to process action items created by watchers,
creating plans and routing them according to Company Handbook rules.

Usage:
    from src.skills.process_inbox import ProcessInboxSkill

    skill = ProcessInboxSkill('./AI_Employee_Vault')
    result = skill.process_all()

    # Or process a single item
    result = skill.process_item('Needs_Action/EMAIL_20260120_urgent.md')
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import re

from src.utils.ralph_wiggum import RalphWiggumLoop, LoopConfig, LoopState
from src.utils.hitl import ApprovalManager


class Priority(Enum):
    """Task priority levels."""
    P0_CRITICAL = "critical"
    P1_HIGH = "high"
    P2_MEDIUM = "medium"
    P3_LOW = "low"


class ActionResult(Enum):
    """Result of processing an action item."""
    PLAN_CREATED = "plan_created"
    AUTO_PROCESSED = "auto_processed"
    PENDING_APPROVAL = "pending_approval"
    NEEDS_REVIEW = "needs_review"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ProcessingResult:
    """Result of processing inbox items."""
    success: bool
    total_items: int = 0
    processed: int = 0
    plans_created: int = 0
    pending_approval: int = 0
    auto_processed: int = 0
    needs_review: int = 0
    errors: int = 0
    items: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ActionItem:
    """Represents an action item from Needs_Action folder."""
    filepath: Path
    filename: str
    item_type: str
    priority: str
    status: str
    content: str
    metadata: Dict[str, Any]
    created: Optional[str] = None

    @classmethod
    def from_file(cls, filepath: Path) -> 'ActionItem':
        """Parse an action file into an ActionItem."""
        content = filepath.read_text(encoding='utf-8')
        metadata = {}
        item_type = "unknown"
        priority = "medium"
        status = "pending"
        created = None

        # Parse YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                content_body = parts[2]

                # Extract fields from frontmatter
                for line in frontmatter.strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')
                        metadata[key] = value

                        if key == 'type':
                            item_type = value
                        elif key == 'priority':
                            priority = value
                        elif key == 'status':
                            status = value
                        elif key == 'created':
                            created = value

                content = content_body

        return cls(
            filepath=filepath,
            filename=filepath.name,
            item_type=item_type,
            priority=priority,
            status=status,
            content=content,
            metadata=metadata,
            created=created
        )


class ProcessInboxSkill:
    """
    Skill to process all items in the Needs_Action folder.

    Uses the Ralph Wiggum Loop for intelligent processing of action items,
    creating plans and routing them according to Company Handbook rules.
    """

    def __init__(
        self,
        vault_path: str,
        use_reasoning_loop: bool = True,
        max_iterations: int = 5
    ):
        """
        Initialize the ProcessInboxSkill.

        Args:
            vault_path: Path to the Obsidian vault
            use_reasoning_loop: Whether to use Ralph Wiggum Loop for processing
            max_iterations: Maximum iterations for reasoning loop per item
        """
        self.vault_path = Path(vault_path)
        self.use_reasoning_loop = use_reasoning_loop
        self.max_iterations = max_iterations

        # Vault folders
        self.needs_action_path = self.vault_path / 'Needs_Action'
        self.plans_path = self.vault_path / 'Plans'
        self.pending_approval_path = self.vault_path / 'Pending_Approval'
        self.done_path = self.vault_path / 'Done'
        self.logs_path = self.vault_path / 'Logs'

        # Ensure folders exist
        for path in [self.needs_action_path, self.plans_path,
                     self.pending_approval_path, self.done_path, self.logs_path]:
            path.mkdir(parents=True, exist_ok=True)

        # Setup components
        self.logger = logging.getLogger('ProcessInboxSkill')
        self.approval_manager = ApprovalManager(str(self.vault_path))

        # Load context
        self._handbook_rules: Dict[str, Any] = {}
        self._business_goals: str = ""
        self._load_context()

        # Setup reasoning loop if enabled
        self.reasoning_loop: Optional[RalphWiggumLoop] = None
        if use_reasoning_loop:
            config = LoopConfig(
                max_iterations=max_iterations,
                timeout_seconds=180,
                cooldown_seconds=1.0,
                completion_promise="ITEM_PROCESSED",
                enable_hitl=True
            )
            self.reasoning_loop = RalphWiggumLoop(str(self.vault_path), config=config)

    def _load_context(self) -> None:
        """Load handbook rules and business goals."""
        # Load Company Handbook
        handbook_path = self.vault_path / 'Company_Handbook.md'
        if handbook_path.exists():
            content = handbook_path.read_text(encoding='utf-8')
            self._handbook_rules = self._parse_handbook(content)
            self.logger.info("Loaded Company Handbook rules")

        # Load Business Goals
        goals_path = self.vault_path / 'Business_Goals.md'
        if goals_path.exists():
            self._business_goals = goals_path.read_text(encoding='utf-8')
            self.logger.info("Loaded Business Goals")

    def _parse_handbook(self, content: str) -> Dict[str, Any]:
        """Parse handbook content into structured rules."""
        rules = {
            'payment_auto_approve_threshold': 50,
            'payment_require_approval_threshold': 100,
            'require_approval_types': ['payment', 'post_social', 'external_email'],
            'auto_process_types': ['file_drop', 'internal_note'],
            'critical_keywords': ['urgent', 'asap', 'critical', 'emergency'],
        }

        # Extract thresholds from content
        threshold_pattern = r'\$(\d+)'
        thresholds = re.findall(threshold_pattern, content)
        if thresholds:
            values = [int(t) for t in thresholds]
            if len(values) >= 2:
                rules['payment_auto_approve_threshold'] = min(values)
                rules['payment_require_approval_threshold'] = max(values)

        return rules

    def process_all(self) -> ProcessingResult:
        """
        Process all items in the Needs_Action folder.

        Returns:
            ProcessingResult with summary of processing
        """
        result = ProcessingResult(success=True)

        # Get all action items
        action_files = list(self.needs_action_path.glob('*.md'))
        result.total_items = len(action_files)

        if not action_files:
            self.logger.info("No items in Needs_Action folder")
            return result

        self.logger.info(f"Processing {len(action_files)} items from Needs_Action")

        # Sort by priority (critical items first)
        items = []
        for filepath in action_files:
            try:
                item = ActionItem.from_file(filepath)
                items.append(item)
            except Exception as e:
                self.logger.error(f"Error parsing {filepath}: {e}")
                result.errors += 1

        # Sort: critical > high > medium > low
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        items.sort(key=lambda x: priority_order.get(x.priority, 3))

        # Process each item
        for item in items:
            try:
                item_result = self.process_item(item)
                result.items.append(item_result)

                if item_result.get('result') == ActionResult.PLAN_CREATED.value:
                    result.plans_created += 1
                elif item_result.get('result') == ActionResult.AUTO_PROCESSED.value:
                    result.auto_processed += 1
                elif item_result.get('result') == ActionResult.PENDING_APPROVAL.value:
                    result.pending_approval += 1
                elif item_result.get('result') == ActionResult.NEEDS_REVIEW.value:
                    result.needs_review += 1
                elif item_result.get('result') == ActionResult.ERROR.value:
                    result.errors += 1

                result.processed += 1

            except Exception as e:
                self.logger.error(f"Error processing {item.filename}: {e}")
                result.errors += 1
                result.items.append({
                    'filename': item.filename,
                    'result': ActionResult.ERROR.value,
                    'error': str(e)
                })

        # Update dashboard
        self._update_dashboard(result)

        # Log summary
        self._log_processing(result)

        return result

    def process_item(self, item: ActionItem) -> Dict[str, Any]:
        """
        Process a single action item.

        Args:
            item: The ActionItem to process

        Returns:
            Dictionary with processing result
        """
        result = {
            'filename': item.filename,
            'item_type': item.item_type,
            'priority': item.priority,
            'result': ActionResult.SKIPPED.value,
        }

        # Determine action based on item type and rules
        requires_approval = self._requires_approval(item)

        if self.use_reasoning_loop and self.reasoning_loop:
            # Use reasoning loop for intelligent processing
            loop_result = self._process_with_reasoning_loop(item)
            result['loop_id'] = loop_result.loop_id
            result['iterations'] = loop_result.iterations
            result['status'] = loop_result.status

            if loop_result.status == 'completed':
                result['result'] = ActionResult.PLAN_CREATED.value
            elif loop_result.status in ('waiting_approval', 'rejected'):
                result['result'] = ActionResult.PENDING_APPROVAL.value
            else:
                result['result'] = ActionResult.NEEDS_REVIEW.value
        else:
            # Simple rule-based processing
            if requires_approval:
                # Create plan and route to Pending_Approval
                plan_path = self._create_plan(item, requires_approval=True)
                self._route_to_pending_approval(item, plan_path)
                result['result'] = ActionResult.PENDING_APPROVAL.value
                result['plan_path'] = str(plan_path)

            elif item.item_type in self._handbook_rules.get('auto_process_types', []):
                # Auto-process and move to Done
                self._auto_process(item)
                result['result'] = ActionResult.AUTO_PROCESSED.value

            else:
                # Create plan for manual review
                plan_path = self._create_plan(item, requires_approval=False)
                result['result'] = ActionResult.PLAN_CREATED.value
                result['plan_path'] = str(plan_path)

        return result

    def _requires_approval(self, item: ActionItem) -> bool:
        """Check if an item requires human approval."""
        # Type-based rules
        if item.item_type in self._handbook_rules.get('require_approval_types', []):
            return True

        # Check for payment amount
        if item.item_type == 'payment':
            amount = item.metadata.get('amount', 0)
            try:
                amount = float(str(amount).replace('$', '').replace(',', ''))
                if amount > self._handbook_rules.get('payment_require_approval_threshold', 100):
                    return True
            except:
                return True  # If can't parse amount, require approval

        # Check metadata
        if item.metadata.get('requires_approval', '').lower() == 'true':
            return True

        return False

    def _process_with_reasoning_loop(self, item: ActionItem) -> LoopState:
        """Process item using the Ralph Wiggum reasoning loop."""
        prompt = self._build_processing_prompt(item)

        return self.reasoning_loop.start_loop(
            prompt=prompt,
            task_file=item.filepath,
            completion_promise="ITEM_PROCESSED"
        )

    def _build_processing_prompt(self, item: ActionItem) -> str:
        """Build a prompt for the reasoning loop to process an item."""
        return f"""# Process Action Item

You are an AI Employee assistant. Process the following action item from the Needs_Action folder.

## Item Details

**Filename**: {item.filename}
**Type**: {item.item_type}
**Priority**: {item.priority}
**Status**: {item.status}
**Created**: {item.created or 'Unknown'}

## Item Content

{item.content}

## Metadata

```json
{json.dumps(item.metadata, indent=2)}
```

## Company Handbook Rules

Payment thresholds:
- Auto-approve: < ${self._handbook_rules.get('payment_auto_approve_threshold', 50)}
- Require approval: > ${self._handbook_rules.get('payment_require_approval_threshold', 100)}

Types requiring approval: {', '.join(self._handbook_rules.get('require_approval_types', []))}

## Your Tasks

1. Analyze this item and determine what actions are needed
2. Create a plan file in Plans/ folder with:
   - Analysis of the item
   - Proposed actions (numbered checklist)
   - Handbook rules that apply
   - Whether approval is required
3. Route the item appropriately:
   - If requires approval → Output REQUIRES_APPROVAL with action details
   - If can be auto-processed → Execute and move to Done/
   - If needs review → Flag for human review

## Plan File Template

Create a file named `PLAN_{{timestamp}}_{{type}}.md` in Plans/ with this structure:

```markdown
---
type: plan
source_file: "{item.filename}"
created: "{{ISO_timestamp}}"
priority: "{item.priority}"
requires_approval: {{true|false}}
status: pending
---

# Plan: {{Brief Description}}

## Source Item
- **File**: {item.filename}
- **Type**: {item.item_type}
- **Received**: {item.created or 'Unknown'}

## Analysis

{{Your analysis here}}

## Proposed Actions

1. [ ] {{Action 1}}
2. [ ] {{Action 2}}

## Handbook Rules Applied

- {{Rule references}}

## Approval Required

{{Yes/No and reason}}
```

When complete, output: <promise>ITEM_PROCESSED</promise>
"""

    def _create_plan(self, item: ActionItem, requires_approval: bool) -> Path:
        """Create a plan file for an action item."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_type = item.item_type.replace(' ', '_')
        filename = f'PLAN_{timestamp}_{safe_type}.md'
        plan_path = self.plans_path / filename

        content = f"""---
type: plan
source_file: "{item.filename}"
created: "{datetime.now().isoformat()}"
priority: "{item.priority}"
requires_approval: {str(requires_approval).lower()}
status: pending
---

# Plan: Process {item.item_type.replace('_', ' ').title()}

## Source Item
- **File**: {item.filename}
- **Type**: {item.item_type}
- **Priority**: {item.priority}
- **Received**: {item.created or 'Unknown'}

## Analysis

This item was automatically analyzed based on Company Handbook rules.

Type: {item.item_type}
Requires Approval: {'Yes' if requires_approval else 'No'}

## Item Content Preview

{item.content[:500]}{'...' if len(item.content) > 500 else ''}

## Proposed Actions

1. [ ] Review item content
2. [ ] {'Await human approval' if requires_approval else 'Process according to rules'}
3. [ ] Update relevant systems
4. [ ] Archive to Done folder

## Handbook Rules Applied

- Item type '{item.item_type}' {'requires' if requires_approval else 'does not require'} human approval
- Priority level: {item.priority}

## Approval Required

{'**Yes** - This item type requires human approval per Company Handbook.' if requires_approval else '**No** - Can be auto-processed.'}

## Metadata

```json
{json.dumps(item.metadata, indent=2)}
```

---
*Plan auto-generated by ProcessInboxSkill*
"""

        plan_path.write_text(content, encoding='utf-8')
        self.logger.info(f"Created plan: {filename}")
        return plan_path

    def _route_to_pending_approval(self, item: ActionItem, plan_path: Path) -> Path:
        """Create an approval request for an item."""
        return self.approval_manager.create_approval_request(
            action_type=item.item_type,
            details={
                'source_file': item.filename,
                'plan_file': plan_path.name,
                'priority': item.priority,
                'metadata': item.metadata
            },
            source_file=item.filename,
            reason=f"Item type '{item.item_type}' requires human approval",
            urgency='high' if item.priority in ('critical', 'high') else 'normal'
        )

    def _auto_process(self, item: ActionItem) -> None:
        """Auto-process an item and move to Done."""
        # Move to Done folder
        dest_path = self.done_path / item.filename
        item.filepath.rename(dest_path)
        self.logger.info(f"Auto-processed and moved to Done: {item.filename}")

    def _update_dashboard(self, result: ProcessingResult) -> None:
        """Update the dashboard with processing summary."""
        dashboard_path = self.vault_path / 'Dashboard.md'

        if not dashboard_path.exists():
            return

        try:
            content = dashboard_path.read_text(encoding='utf-8')

            # Create summary section
            summary = f"""
## Last Inbox Processing

**Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

| Metric | Count |
|--------|-------|
| Total Items | {result.total_items} |
| Processed | {result.processed} |
| Plans Created | {result.plans_created} |
| Auto-Processed | {result.auto_processed} |
| Pending Approval | {result.pending_approval} |
| Needs Review | {result.needs_review} |
| Errors | {result.errors} |

"""

            # Insert or update the section
            marker = "## Last Inbox Processing"
            if marker in content:
                # Find and replace existing section
                start = content.find(marker)
                next_section = content.find("\n## ", start + len(marker))
                if next_section == -1:
                    content = content[:start] + summary
                else:
                    content = content[:start] + summary + content[next_section:]
            else:
                # Add before "## Recent Activity" or at end
                if "## Recent Activity" in content:
                    content = content.replace("## Recent Activity", summary + "## Recent Activity")
                else:
                    content += summary

            dashboard_path.write_text(content, encoding='utf-8')
            self.logger.info("Updated dashboard")

        except Exception as e:
            self.logger.warning(f"Error updating dashboard: {e}")

    def _log_processing(self, result: ProcessingResult) -> None:
        """Log processing result to daily log file."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        entry = {
            'timestamp': datetime.now().isoformat(),
            'component': 'ProcessInboxSkill',
            'action': 'process_all',
            'result': result.to_dict()
        }

        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text(encoding='utf-8'))
            except:
                logs = []

        logs.append(entry)
        log_file.write_text(json.dumps(logs, indent=2), encoding='utf-8')

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the inbox processing skill."""
        pending_count = len(list(self.needs_action_path.glob('*.md')))
        plans_count = len(list(self.plans_path.glob('*.md')))
        approval_count = len(list(self.pending_approval_path.glob('*.md')))

        return {
            'skill': 'ProcessInboxSkill',
            'vault_path': str(self.vault_path),
            'use_reasoning_loop': self.use_reasoning_loop,
            'pending_items': pending_count,
            'plans_count': plans_count,
            'pending_approval': approval_count,
            'handbook_loaded': bool(self._handbook_rules),
        }
