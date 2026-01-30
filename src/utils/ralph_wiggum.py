"""
Ralph Wiggum Loop - Claude Reasoning Loop

Keeps Claude Code working on a task until it is complete.
This is the core reasoning mechanism for the AI Employee system.

The pattern:
1. Orchestrator creates state file with prompt
2. Claude works on task
3. Claude tries to exit
4. Stop hook checks: Is task complete?
5. NO -> Block exit, re-inject prompt with context
6. YES -> Allow exit, task complete

Usage:
    from src.utils.ralph_wiggum import RalphWiggumLoop, LoopConfig

    loop = RalphWiggumLoop('./AI_Employee_Vault')
    result = loop.start_loop(
        prompt="Process the invoice in Needs_Action/invoice.md",
        task_file=Path("Needs_Action/FILE_20260120_invoice.md")
    )

    print(f"Status: {result.status}")
    print(f"Iterations: {result.iterations}")
"""

import os
import json
import subprocess
import logging
import time
import uuid
import re
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass, field, asdict

# Import HITL components
try:
    from src.utils.hitl import ApprovalManager, ApprovalWatcher, ApprovalStatus
    HITL_AVAILABLE = True
except ImportError:
    HITL_AVAILABLE = False


@dataclass
class LoopConfig:
    """Configuration for the Ralph Wiggum Loop."""
    max_iterations: int = 10
    timeout_seconds: int = 300  # Per-iteration timeout
    max_output_chars: int = 2000  # Truncation limit for context
    context_iterations: int = 3  # How many previous outputs to include
    cooldown_seconds: float = 2.0  # Pause between iterations
    completion_promise: str = "TASK_COMPLETE"
    claude_command: str = "claude"  # Claude CLI command
    working_dir: Optional[str] = None  # Override working directory
    enable_hitl: bool = True  # Enable HITL approval workflow
    approval_timeout_hours: int = 24  # How long to wait for approval
    approval_check_interval: int = 5  # Seconds between approval checks


@dataclass
class IterationResult:
    """Result from a single Claude iteration."""
    iteration: int
    started: str
    completed: str
    duration_seconds: float
    output: str
    output_truncated: bool
    exit_code: int
    error: Optional[str] = None
    timed_out: bool = False


@dataclass
class LoopState:
    """Persistent state for a running loop."""
    loop_id: str
    prompt: str
    task_file: Optional[str]
    completion_promise: str
    started: str
    last_updated: str
    iterations: int
    status: str  # 'running', 'completed', 'max_iterations', 'error', 'timeout', 'waiting_approval'
    outputs: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None
    approval_request: Optional[str] = None  # Path to approval request file
    approval_action_type: Optional[str] = None  # Type of action awaiting approval
    approval_details: Optional[Dict[str, Any]] = None  # Details of the action
    approval_reason: Optional[str] = None  # Why approval is needed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LoopState':
        """Create from dictionary."""
        return cls(**data)


class CompletionStrategy(ABC):
    """Abstract base class for completion checking strategies."""

    @abstractmethod
    def is_complete(self, output: str, state: LoopState, vault_path: Path) -> bool:
        """
        Check if the task is complete.

        Args:
            output: The output from the current iteration
            state: Current loop state
            vault_path: Path to the vault

        Returns:
            True if task is complete
        """
        pass

    @property
    def name(self) -> str:
        """Human-readable strategy name."""
        return self.__class__.__name__


class PromiseCompletion(CompletionStrategy):
    """
    Check for completion promise string in output.

    Looks for exact match or XML-wrapped promise:
    - "TASK_COMPLETE"
    - "<promise>TASK_COMPLETE</promise>"
    """

    def __init__(self, promise: str = "TASK_COMPLETE"):
        self.promise = promise

    def is_complete(self, output: str, state: LoopState, vault_path: Path) -> bool:
        # Check for exact promise
        if self.promise in output:
            return True

        # Check for XML-style wrapper
        if f"<promise>{self.promise}</promise>" in output:
            return True

        return False


class FileMovementCompletion(CompletionStrategy):
    """
    Check if task file moved from Needs_Action to Done.

    This strategy considers the task complete when the original
    task file no longer exists in Needs_Action and exists in Done.
    """

    def is_complete(self, output: str, state: LoopState, vault_path: Path) -> bool:
        if not state.task_file:
            return False

        task_name = Path(state.task_file).name
        original_location = vault_path / 'Needs_Action' / task_name
        done_location = vault_path / 'Done' / task_name

        # Complete if file is in Done and not in Needs_Action
        if done_location.exists() and not original_location.exists():
            return True

        # Also check if Needs_Action is completely empty (all tasks done)
        needs_action = vault_path / 'Needs_Action'
        if needs_action.exists() and not any(needs_action.glob('*.md')):
            return True

        return False


class CustomCompletion(CompletionStrategy):
    """
    User-provided callback function for completion checking.

    The callback should have signature:
        callback(output: str, state: LoopState, vault_path: Path) -> bool
    """

    def __init__(self, callback: Callable[[str, LoopState, Path], bool], name: str = "CustomCompletion"):
        self.callback = callback
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def is_complete(self, output: str, state: LoopState, vault_path: Path) -> bool:
        try:
            return self.callback(output, state, vault_path)
        except Exception as e:
            logging.getLogger('CustomCompletion').error(f"Callback error: {e}")
            return False


class CompositeCompletion(CompletionStrategy):
    """
    Combine multiple completion strategies with OR logic.

    Returns True if ANY strategy returns True.
    """

    def __init__(self, strategies: List[CompletionStrategy]):
        self.strategies = strategies

    def is_complete(self, output: str, state: LoopState, vault_path: Path) -> bool:
        for strategy in self.strategies:
            try:
                if strategy.is_complete(output, state, vault_path):
                    logging.getLogger('CompositeCompletion').debug(
                        f"Completion detected by {strategy.name}"
                    )
                    return True
            except Exception as e:
                logging.getLogger('CompositeCompletion').warning(
                    f"Strategy {strategy.name} error: {e}"
                )
        return False


class RalphWiggumLoop:
    """
    Main reasoning loop class.

    Manages persistent Claude Code sessions that loop until task completion.
    """

    def __init__(
        self,
        vault_path: str,
        config: Optional[LoopConfig] = None,
        completion_strategies: Optional[List[CompletionStrategy]] = None
    ):
        """
        Initialize the reasoning loop.

        Args:
            vault_path: Path to the Obsidian vault
            config: Loop configuration (uses defaults if None)
            completion_strategies: List of completion strategies (uses PromiseCompletion if None)
        """
        self.vault_path = Path(vault_path)
        self.config = config or LoopConfig()
        self.logs_path = self.vault_path / 'Logs'
        self.state_dir = self.vault_path / '.ralph_states'

        # Ensure directories exist
        self.logs_path.mkdir(parents=True, exist_ok=True)
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Setup completion strategies
        if completion_strategies:
            self.completion_checker = CompositeCompletion(completion_strategies)
        else:
            # Default: check for promise and file movement
            self.completion_checker = CompositeCompletion([
                PromiseCompletion(self.config.completion_promise),
                FileMovementCompletion()
            ])

        # Setup logging
        self.logger = logging.getLogger('RalphWiggumLoop')

        # Setup HITL approval manager
        self.approval_manager: Optional['ApprovalManager'] = None
        if self.config.enable_hitl and HITL_AVAILABLE:
            self.approval_manager = ApprovalManager(str(self.vault_path))
            self.logger.info("HITL approval workflow enabled")
        elif self.config.enable_hitl and not HITL_AVAILABLE:
            self.logger.warning("HITL requested but not available - install src.utils.hitl")

        # Track loops waiting for approval (loop_id -> approval_path)
        self._waiting_approval: Dict[str, str] = {}

    def start_loop(
        self,
        prompt: str,
        task_file: Optional[Path] = None,
        completion_promise: Optional[str] = None
    ) -> LoopState:
        """
        Start a new reasoning loop.

        Args:
            prompt: The initial task prompt for Claude
            task_file: Path to the task file that triggered this loop
            completion_promise: Override completion promise (uses config default if None)

        Returns:
            Final LoopState with results
        """
        # Generate loop ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        short_uuid = uuid.uuid4().hex[:6]
        loop_id = f"ralph_{timestamp}_{short_uuid}"

        # Create initial state
        state = LoopState(
            loop_id=loop_id,
            prompt=prompt,
            task_file=str(task_file) if task_file else None,
            completion_promise=completion_promise or self.config.completion_promise,
            started=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            iterations=0,
            status='running',
            outputs=[]
        )

        self._save_state(state)
        self._log_event('loop_started', {
            'loop_id': loop_id,
            'task_file': state.task_file,
            'prompt_preview': prompt[:200]
        })

        self.logger.info(f"Starting loop {loop_id}")

        # Main loop
        while state.iterations < self.config.max_iterations:
            state.iterations += 1
            state.last_updated = datetime.now().isoformat()

            # Build evolved prompt with context
            evolved_prompt = self._build_evolved_prompt(prompt, state)

            # Run Claude
            self.logger.info(f"Loop {loop_id}: iteration {state.iterations}/{self.config.max_iterations}")
            result = self._run_claude(evolved_prompt, state.iterations)

            # Store result
            state.outputs.append(asdict(result))
            self._save_state(state)

            # Log iteration
            self._log_event('loop_iteration', {
                'loop_id': loop_id,
                'iteration': result.iteration,
                'duration_seconds': result.duration_seconds,
                'exit_code': result.exit_code,
                'output_preview': result.output[:200] if result.output else None
            })

            # Check for errors
            if result.error and not result.timed_out:
                state.status = 'error'
                state.error = result.error
                self._save_state(state)
                self.logger.error(f"Loop {loop_id}: error - {result.error}")
                break

            # Check for timeout
            if result.timed_out:
                state.status = 'timeout'
                state.error = f"Iteration {state.iterations} timed out after {self.config.timeout_seconds}s"
                self._save_state(state)
                self.logger.warning(f"Loop {loop_id}: timeout at iteration {state.iterations}")
                break

            # Check for completion
            if self._check_completion(result.output, state):
                state.status = 'completed'
                self._save_state(state)
                self.logger.info(f"Loop {loop_id}: completed after {state.iterations} iterations")
                break

            # Check if requires approval (full HITL integration)
            approval_info = self._extract_approval_request(result.output)
            if approval_info:
                action_type, details, reason = approval_info
                self.logger.info(f"Loop {loop_id}: approval required for {action_type}")

                # Create approval request if HITL is enabled
                if self.approval_manager:
                    approval_path = self._create_approval_request(
                        state=state,
                        action_type=action_type,
                        details=details,
                        reason=reason
                    )

                    # Update state
                    state.status = 'waiting_approval'
                    state.approval_request = str(approval_path)
                    state.approval_action_type = action_type
                    state.approval_details = details
                    state.approval_reason = reason
                    state.last_updated = datetime.now().isoformat()
                    self._save_state(state)

                    # Track this loop as waiting for approval
                    self._waiting_approval[loop_id] = str(approval_path)

                    self._log_event('loop_waiting_approval', {
                        'loop_id': loop_id,
                        'action_type': action_type,
                        'approval_path': str(approval_path)
                    })

                    # Wait for approval or timeout
                    approved = self._wait_for_approval(state, approval_path)

                    if approved:
                        # Approval granted - continue loop
                        self.logger.info(f"Loop {loop_id}: approval granted, continuing")
                        state.status = 'running'
                        state.last_updated = datetime.now().isoformat()
                        self._save_state(state)
                        # Don't break - continue to next iteration
                    else:
                        # Approval rejected or timed out
                        state.status = 'rejected' if self._is_approval_rejected(approval_path) else 'approval_timeout'
                        state.error = "Approval was rejected" if state.status == 'rejected' else "Approval request timed out"
                        self._save_state(state)
                        self.logger.info(f"Loop {loop_id}: {state.status}")
                        break
                else:
                    # No HITL - just log and continue
                    self.logger.warning(f"Loop {loop_id}: approval needed but HITL not available")

            # Cooldown before next iteration
            if state.iterations < self.config.max_iterations:
                time.sleep(self.config.cooldown_seconds)

        # Check if we hit max iterations
        if state.status == 'running' and state.iterations >= self.config.max_iterations:
            state.status = 'max_iterations'
            self._save_state(state)
            self.logger.warning(f"Loop {loop_id}: max iterations ({self.config.max_iterations}) reached")

        # Log completion
        self._log_event('loop_finished', {
            'loop_id': loop_id,
            'status': state.status,
            'iterations': state.iterations,
            'total_duration': self._calculate_total_duration(state)
        })

        # Update dashboard
        self._update_dashboard(state)

        return state

    def resume_loop(self, loop_id: str) -> Optional[LoopState]:
        """
        Resume an interrupted loop from saved state.

        Args:
            loop_id: ID of the loop to resume

        Returns:
            Resumed LoopState or None if not found
        """
        state = self._load_state(loop_id)
        if not state:
            self.logger.warning(f"Cannot resume loop {loop_id}: state not found")
            return None

        if state.status not in ('running', 'waiting_approval'):
            self.logger.warning(f"Cannot resume loop {loop_id}: status is {state.status}")
            return state

        self.logger.info(f"Resuming loop {loop_id} from iteration {state.iterations}")

        # Continue the loop from where it left off
        while state.iterations < self.config.max_iterations:
            state.iterations += 1
            state.last_updated = datetime.now().isoformat()

            evolved_prompt = self._build_evolved_prompt(state.prompt, state)
            result = self._run_claude(evolved_prompt, state.iterations)

            state.outputs.append(asdict(result))
            self._save_state(state)

            if result.error or result.timed_out:
                state.status = 'error' if result.error else 'timeout'
                state.error = result.error or f"Timeout at iteration {state.iterations}"
                self._save_state(state)
                break

            if self._check_completion(result.output, state):
                state.status = 'completed'
                self._save_state(state)
                break

            if state.iterations < self.config.max_iterations:
                time.sleep(self.config.cooldown_seconds)

        if state.status == 'running' and state.iterations >= self.config.max_iterations:
            state.status = 'max_iterations'
            self._save_state(state)

        return state

    def get_active_loops(self) -> List[LoopState]:
        """Get all active (running) loops."""
        active = []
        for state_file in self.state_dir.glob('*.json'):
            try:
                state = self._load_state(state_file.stem)
                if state and state.status in ('running', 'waiting_approval'):
                    active.append(state)
            except Exception as e:
                self.logger.warning(f"Error loading state {state_file}: {e}")
        return active

    def get_loops_waiting_approval(self) -> List[LoopState]:
        """Get all loops currently waiting for human approval."""
        waiting = []
        for state_file in self.state_dir.glob('*.json'):
            try:
                state = self._load_state(state_file.stem)
                if state and state.status == 'waiting_approval':
                    waiting.append(state)
            except Exception as e:
                self.logger.warning(f"Error loading state {state_file}: {e}")
        return waiting

    def notify_approval(self, loop_id: str, approved: bool) -> bool:
        """
        Notify a waiting loop that approval decision was made.

        This can be called by external systems (like the orchestrator's
        ApprovalWatcher) when an approval is granted or rejected.

        Args:
            loop_id: ID of the loop waiting for approval
            approved: True if approved, False if rejected

        Returns:
            True if notification was successful
        """
        state = self._load_state(loop_id)
        if not state:
            self.logger.warning(f"Cannot notify loop {loop_id}: not found")
            return False

        if state.status != 'waiting_approval':
            self.logger.warning(f"Loop {loop_id} is not waiting for approval (status: {state.status})")
            return False

        # Update state based on decision
        if approved:
            state.status = 'running'
            self._log_event('approval_notification', {
                'loop_id': loop_id,
                'decision': 'approved'
            })
        else:
            state.status = 'rejected'
            state.error = 'Approval was rejected by human reviewer'
            self._log_event('approval_notification', {
                'loop_id': loop_id,
                'decision': 'rejected'
            })

        state.last_updated = datetime.now().isoformat()
        self._save_state(state)

        self.logger.info(f"Loop {loop_id}: approval {'granted' if approved else 'rejected'}")
        return True

    def _run_claude(self, prompt: str, iteration: int) -> IterationResult:
        """
        Execute Claude Code subprocess.

        Args:
            prompt: The prompt to send to Claude
            iteration: Current iteration number

        Returns:
            IterationResult with output and metadata
        """
        started = datetime.now()
        result = IterationResult(
            iteration=iteration,
            started=started.isoformat(),
            completed='',
            duration_seconds=0,
            output='',
            output_truncated=False,
            exit_code=-1
        )

        try:
            # Create temporary prompt file
            prompt_file = self.state_dir / f'.prompt_{iteration}_{uuid.uuid4().hex[:6]}.md'
            prompt_file.write_text(prompt, encoding='utf-8')

            # Determine working directory
            cwd = self.config.working_dir or str(self.vault_path)

            # Run Claude Code
            proc = subprocess.run(
                [self.config.claude_command, '--print', '-p', str(prompt_file)],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=self.config.timeout_seconds
            )

            result.output = proc.stdout + proc.stderr
            result.exit_code = proc.returncode

        except subprocess.TimeoutExpired:
            result.timed_out = True
            result.error = f"Timeout after {self.config.timeout_seconds}s"
            self.logger.warning(f"Iteration {iteration} timed out")

        except FileNotFoundError:
            result.error = f"Claude command not found: {self.config.claude_command}"
            self.logger.error(result.error)

        except Exception as e:
            result.error = str(e)
            self.logger.error(f"Iteration {iteration} error: {e}")

        finally:
            completed = datetime.now()
            result.completed = completed.isoformat()
            result.duration_seconds = (completed - started).total_seconds()

            # Cleanup prompt file
            if 'prompt_file' in locals():
                prompt_file.unlink(missing_ok=True)

        return result

    def _build_evolved_prompt(self, original_prompt: str, state: LoopState) -> str:
        """
        Build prompt with context from previous iterations.

        Args:
            original_prompt: The original task prompt
            state: Current loop state

        Returns:
            Evolved prompt with previous context
        """
        if state.iterations <= 1 or not state.outputs:
            return original_prompt

        # Get recent outputs (last N iterations)
        recent_outputs = state.outputs[-self.config.context_iterations:]

        # Build context section
        context_parts = []
        for output_data in recent_outputs:
            iteration = output_data.get('iteration', '?')
            output_text = output_data.get('output', '')

            # Truncate if needed
            if len(output_text) > self.config.max_output_chars:
                output_text = output_text[:self.config.max_output_chars] + "\n[... output truncated ...]"

            context_parts.append(f"### Iteration {iteration}\n{output_text}")

        context = "\n\n".join(context_parts)

        # Build evolved prompt
        evolved = f"""{original_prompt}

---

## Previous Iterations Context

{context}

---

## Instructions

Continue working on the task above. Review the previous iterations to understand progress.

When the task is FULLY COMPLETE, output: <promise>{state.completion_promise}</promise>

If you need human approval for any action (payments, emails to external recipients, social posts, etc.),
output the approval request in this format:

```
REQUIRES_APPROVAL: action_type

Action: send_email | payment | post_social | delete_file | other
Reason: Brief explanation of why approval is needed

```json
{{"field1": "value1", "field2": "value2"}}
```
```

The loop will pause and wait for human approval before continuing.
"""

        return evolved

    def _check_completion(self, output: str, state: LoopState) -> bool:
        """Check if task is complete using all strategies."""
        return self.completion_checker.is_complete(output, state, self.vault_path)

    def _check_requires_approval(self, output: str) -> bool:
        """Check if Claude's output indicates approval is needed."""
        approval_indicators = [
            "REQUIRES_APPROVAL",
            "NEEDS_HUMAN_REVIEW",
            "PENDING_APPROVAL",
            "AWAIT_APPROVAL"
        ]
        return any(indicator in output for indicator in approval_indicators)

    def _extract_approval_request(self, output: str) -> Optional[Tuple[str, Dict[str, Any], str]]:
        """
        Extract approval request details from Claude's output.

        Parses output looking for patterns like:
        - REQUIRES_APPROVAL: action_type
        - Action: send_email
        - Details: {"to": "...", "subject": "..."}
        - Reason: External recipient

        Args:
            output: Claude's output text

        Returns:
            Tuple of (action_type, details, reason) or None if no approval needed
        """
        if not self._check_requires_approval(output):
            return None

        action_type = "unknown"
        details = {}
        reason = "Human approval required per Company Handbook"

        # Extract action type
        action_patterns = [
            r'REQUIRES_APPROVAL[:\s]+(\w+)',
            r'Action[:\s]+(\w+)',
            r'action_type[:\s]*["\']?(\w+)["\']?',
        ]
        for pattern in action_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                action_type = match.group(1).lower()
                break

        # Extract details (look for JSON block)
        json_patterns = [
            r'```json\s*\n(.*?)\n```',
            r'Details[:\s]*(\{.*?\})',
            r'"details"[:\s]*(\{.*?\})',
        ]
        for pattern in json_patterns:
            match = re.search(pattern, output, re.DOTALL | re.IGNORECASE)
            if match:
                try:
                    details = json.loads(match.group(1))
                    break
                except json.JSONDecodeError:
                    pass

        # If no JSON found, try to extract key-value pairs
        if not details:
            kv_patterns = [
                r'(?:to|recipient)[:\s]*([^\n,]+)',
                r'(?:amount)[:\s]*\$?([\d,]+\.?\d*)',
                r'(?:subject)[:\s]*([^\n]+)',
                r'(?:content|message)[:\s]*([^\n]+)',
            ]
            for pattern in kv_patterns:
                match = re.search(pattern, output, re.IGNORECASE)
                if match:
                    key = pattern.split('[')[0].split('|')[-1].strip('()?:')
                    details[key] = match.group(1).strip()

        # Extract reason
        reason_patterns = [
            r'Reason[:\s]*([^\n]+)',
            r'Why[:\s]*([^\n]+)',
            r'because[:\s]*([^\n]+)',
        ]
        for pattern in reason_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                reason = match.group(1).strip()
                break

        # Infer action type from content if still unknown
        if action_type == "unknown":
            if any(kw in output.lower() for kw in ['email', 'send to', 'mailto']):
                action_type = 'send_email'
            elif any(kw in output.lower() for kw in ['payment', 'pay', 'transfer', 'invoice']):
                action_type = 'payment'
            elif any(kw in output.lower() for kw in ['post', 'linkedin', 'social', 'tweet']):
                action_type = 'post_social'
            elif any(kw in output.lower() for kw in ['delete', 'remove', 'drop']):
                action_type = 'delete_file'

        return (action_type, details, reason)

    def _create_approval_request(
        self,
        state: LoopState,
        action_type: str,
        details: Dict[str, Any],
        reason: str
    ) -> Path:
        """
        Create an approval request file using the ApprovalManager.

        Args:
            state: Current loop state
            action_type: Type of action requiring approval
            details: Action details
            reason: Why approval is needed

        Returns:
            Path to the created approval request file
        """
        if not self.approval_manager:
            raise RuntimeError("ApprovalManager not initialized")

        # Add loop context to details
        enhanced_details = {
            **details,
            '_loop_id': state.loop_id,
            '_iteration': state.iterations,
            '_task_file': state.task_file,
        }

        return self.approval_manager.create_approval_request(
            action_type=action_type,
            details=enhanced_details,
            source_file=Path(state.task_file).name if state.task_file else None,
            reason=reason,
            urgency='normal',
            expires_hours=self.config.approval_timeout_hours
        )

    def _wait_for_approval(self, state: LoopState, approval_path: Path) -> bool:
        """
        Wait for approval, rejection, or timeout.

        Args:
            state: Current loop state
            approval_path: Path to the approval request file

        Returns:
            True if approved, False if rejected or timed out
        """
        if not self.approval_manager:
            return False

        max_wait = self.config.approval_timeout_hours * 3600
        waited = 0

        self.logger.info(f"Waiting for approval (timeout: {self.config.approval_timeout_hours}h)")

        while waited < max_wait:
            status = self.approval_manager.check_status(approval_path)

            if status == ApprovalStatus.APPROVED:
                self._log_event('approval_granted', {
                    'loop_id': state.loop_id,
                    'approval_path': str(approval_path)
                })
                return True

            if status in (ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED):
                self._log_event('approval_denied', {
                    'loop_id': state.loop_id,
                    'approval_path': str(approval_path),
                    'status': status.value
                })
                return False

            # Still pending - wait and check again
            time.sleep(self.config.approval_check_interval)
            waited += self.config.approval_check_interval

            # Update state to show we're still waiting
            if waited % 60 == 0:  # Log every minute
                self.logger.debug(f"Still waiting for approval ({waited}s elapsed)")

        # Timeout
        self._log_event('approval_timeout', {
            'loop_id': state.loop_id,
            'approval_path': str(approval_path),
            'waited_seconds': waited
        })
        return False

    def _is_approval_rejected(self, approval_path: Path) -> bool:
        """Check if an approval request was rejected."""
        if not self.approval_manager:
            return False
        status = self.approval_manager.check_status(approval_path)
        return status == ApprovalStatus.REJECTED

    def _save_state(self, state: LoopState) -> None:
        """Persist state to file."""
        state_file = self.state_dir / f'{state.loop_id}.json'

        # Atomic write: write to temp file then rename
        temp_file = state_file.with_suffix('.tmp')
        temp_file.write_text(
            json.dumps(state.to_dict(), indent=2, default=str),
            encoding='utf-8'
        )
        temp_file.replace(state_file)

    def _load_state(self, loop_id: str) -> Optional[LoopState]:
        """Load state from file."""
        state_file = self.state_dir / f'{loop_id}.json'

        if not state_file.exists():
            return None

        try:
            data = json.loads(state_file.read_text(encoding='utf-8'))
            return LoopState.from_dict(data)
        except Exception as e:
            self.logger.error(f"Error loading state {loop_id}: {e}")
            return None

    def _log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        """Log an event to the daily log file."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_path / f'{today}.json'

        entry = {
            'timestamp': datetime.now().isoformat(),
            'component': 'RalphWiggumLoop',
            'event': event_type,
            'details': details
        }

        logs = []
        if log_file.exists():
            try:
                logs = json.loads(log_file.read_text(encoding='utf-8'))
            except:
                logs = []

        logs.append(entry)
        log_file.write_text(json.dumps(logs, indent=2), encoding='utf-8')

    def _calculate_total_duration(self, state: LoopState) -> float:
        """Calculate total loop duration in seconds."""
        if not state.outputs:
            return 0.0
        return sum(o.get('duration_seconds', 0) for o in state.outputs)

    def _update_dashboard(self, state: LoopState) -> None:
        """Update Dashboard.md with loop status."""
        dashboard_path = self.vault_path / 'Dashboard.md'

        if not dashboard_path.exists():
            return

        try:
            content = dashboard_path.read_text(encoding='utf-8')

            # Find or create reasoning loops section
            loop_section_marker = "## Reasoning Loops"

            # Build status emoji
            status_emoji = {
                'running': 'running',
                'completed': 'done',
                'max_iterations': 'warning',
                'error': 'error',
                'timeout': 'timeout',
                'waiting_approval': 'waiting'
            }.get(state.status, state.status)

            # Build loop info
            task_name = Path(state.task_file).name if state.task_file else 'N/A'
            loop_info = f"| {state.loop_id[:20]}... | {task_name[:30]} | {state.iterations}/{self.config.max_iterations} | {status_emoji} | {state.started[:19]} |"

            if loop_section_marker in content:
                # Update existing section - simplified approach
                # In production, this would parse and update the table properly
                pass
            else:
                # Add new section before "## Recent Activity" or at end
                new_section = f"""
## Reasoning Loops

| Loop ID | Task | Iterations | Status | Started |
|---------|------|------------|--------|---------|
{loop_info}

"""
                if "## Recent Activity" in content:
                    content = content.replace("## Recent Activity", new_section + "## Recent Activity")
                else:
                    content += new_section

                dashboard_path.write_text(content, encoding='utf-8')

        except Exception as e:
            self.logger.warning(f"Error updating dashboard: {e}")


# CLI interface
def main():
    """CLI entry point for the Ralph Wiggum Loop."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Ralph Wiggum Loop - Keep Claude working until task is complete',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Start a new loop with a prompt
  python -m src.utils.ralph_wiggum --vault ./AI_Employee_Vault "Process all invoices in Inbox"

  # Start with a task file
  python -m src.utils.ralph_wiggum --vault ./AI_Employee_Vault --task Needs_Action/invoice.md "Process this invoice"

  # Resume an interrupted loop
  python -m src.utils.ralph_wiggum --vault ./AI_Employee_Vault --resume ralph_20260120_143052_a1b2c3

  # Custom settings
  python -m src.utils.ralph_wiggum --vault ./AI_Employee_Vault --max-iterations 5 --timeout 120 "Quick task"
        '''
    )

    parser.add_argument(
        'prompt',
        nargs='?',
        help='Task prompt for Claude'
    )
    parser.add_argument(
        '--vault',
        default='./AI_Employee_Vault',
        help='Path to Obsidian vault'
    )
    parser.add_argument(
        '--task',
        help='Path to task file (relative to vault)'
    )
    parser.add_argument(
        '--resume',
        help='Resume a loop by ID'
    )
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=10,
        help='Maximum iterations (default: 10)'
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Per-iteration timeout in seconds (default: 300)'
    )
    parser.add_argument(
        '--completion-promise',
        default='TASK_COMPLETE',
        help='Completion promise string (default: TASK_COMPLETE)'
    )
    parser.add_argument(
        '--list-active',
        action='store_true',
        help='List active loops'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create config
    config = LoopConfig(
        max_iterations=args.max_iterations,
        timeout_seconds=args.timeout,
        completion_promise=args.completion_promise
    )

    # Create loop instance
    loop = RalphWiggumLoop(args.vault, config=config)

    # Handle commands
    if args.list_active:
        active = loop.get_active_loops()
        if active:
            print(f"\nActive loops ({len(active)}):")
            print("-" * 60)
            for state in active:
                print(f"  {state.loop_id}")
                print(f"    Status: {state.status}")
                print(f"    Iterations: {state.iterations}/{config.max_iterations}")
                print(f"    Task: {state.task_file or 'N/A'}")
                print()
        else:
            print("No active loops")
        return

    if args.resume:
        result = loop.resume_loop(args.resume)
        if result:
            print(f"\nResumed loop: {result.loop_id}")
            print(f"Final status: {result.status}")
            print(f"Total iterations: {result.iterations}")
        else:
            print(f"Failed to resume loop: {args.resume}")
        return

    if not args.prompt:
        parser.error("prompt is required (unless using --resume or --list-active)")

    # Start new loop
    task_file = Path(args.task) if args.task else None

    print(f"\nStarting Ralph Wiggum Loop")
    print(f"Vault: {args.vault}")
    print(f"Max iterations: {args.max_iterations}")
    print(f"Timeout: {args.timeout}s per iteration")
    print("-" * 60)

    result = loop.start_loop(
        prompt=args.prompt,
        task_file=task_file,
        completion_promise=args.completion_promise
    )

    print("-" * 60)
    print(f"Loop ID: {result.loop_id}")
    print(f"Status: {result.status}")
    print(f"Iterations: {result.iterations}")

    if result.error:
        print(f"Error: {result.error}")

    if result.status == 'completed':
        print("\nTask completed successfully!")
    elif result.status == 'max_iterations':
        print(f"\nWarning: Max iterations ({args.max_iterations}) reached without completion")


if __name__ == '__main__':
    main()
