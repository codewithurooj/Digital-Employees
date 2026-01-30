"""
Tests for Ralph Wiggum Loop (Claude Reasoning Loop).

This module tests the persistence mechanism that keeps Claude
working on tasks until completion.
"""

import pytest
from pathlib import Path
from datetime import datetime
import json
import time
from unittest.mock import Mock, patch, MagicMock

from src.utils.ralph_wiggum import (
    RalphWiggumLoop,
    LoopConfig,
    LoopState,
    IterationResult,
    CompletionStrategy,
    PromiseCompletion,
    FileMovementCompletion,
    CustomCompletion,
    CompositeCompletion
)


class TestLoopConfig:
    """Test LoopConfig dataclass."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        config = LoopConfig()

        assert config.max_iterations == 10
        assert config.timeout_seconds == 300
        assert config.max_output_chars == 2000
        assert config.context_iterations == 3
        assert config.cooldown_seconds == 2.0
        assert config.completion_promise == "TASK_COMPLETE"
        assert config.claude_command == "claude"
        assert config.working_dir is None

    def test_custom_values(self):
        """Test that custom values are applied."""
        config = LoopConfig(
            max_iterations=5,
            timeout_seconds=120,
            completion_promise="DONE"
        )

        assert config.max_iterations == 5
        assert config.timeout_seconds == 120
        assert config.completion_promise == "DONE"


class TestLoopState:
    """Test LoopState dataclass."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        state = LoopState(
            loop_id="test_123",
            prompt="Test prompt",
            task_file="test.md",
            completion_promise="TASK_COMPLETE",
            started="2026-01-20T10:00:00",
            last_updated="2026-01-20T10:01:00",
            iterations=1,
            status="running",
            outputs=[],
            error=None
        )

        data = state.to_dict()

        assert data['loop_id'] == "test_123"
        assert data['prompt'] == "Test prompt"
        assert data['status'] == "running"

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            'loop_id': "test_456",
            'prompt': "Another prompt",
            'task_file': None,
            'completion_promise': "DONE",
            'started': "2026-01-20T10:00:00",
            'last_updated': "2026-01-20T10:01:00",
            'iterations': 2,
            'status': "completed",
            'outputs': [],
            'error': None,
            'approval_request': None
        }

        state = LoopState.from_dict(data)

        assert state.loop_id == "test_456"
        assert state.status == "completed"
        assert state.iterations == 2


class TestPromiseCompletion:
    """Test PromiseCompletion strategy."""

    def test_exact_match(self, temp_vault):
        """Test detection of exact completion promise."""
        strategy = PromiseCompletion("TASK_COMPLETE")
        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=None,
            completion_promise="TASK_COMPLETE",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )

        assert strategy.is_complete("Done! TASK_COMPLETE", state, temp_vault)
        assert not strategy.is_complete("Not done yet", state, temp_vault)

    def test_xml_wrapper(self, temp_vault):
        """Test detection of XML-wrapped promise."""
        strategy = PromiseCompletion("TASK_COMPLETE")
        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=None,
            completion_promise="TASK_COMPLETE",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )

        output = "The task is done. <promise>TASK_COMPLETE</promise>"
        assert strategy.is_complete(output, state, temp_vault)

    def test_custom_promise(self, temp_vault):
        """Test custom completion promise."""
        strategy = PromiseCompletion("FINISHED")
        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=None,
            completion_promise="FINISHED",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )

        assert strategy.is_complete("All done! FINISHED", state, temp_vault)
        assert not strategy.is_complete("TASK_COMPLETE", state, temp_vault)


class TestFileMovementCompletion:
    """Test FileMovementCompletion strategy."""

    def test_file_not_moved(self, temp_vault):
        """Test when task file is still in Needs_Action."""
        # Create task file in Needs_Action
        task_file = temp_vault / "Needs_Action" / "task.md"
        task_file.write_text("Test task")

        strategy = FileMovementCompletion()
        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=str(task_file),
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )

        assert not strategy.is_complete("", state, temp_vault)

    def test_file_moved_to_done(self, temp_vault):
        """Test when task file has been moved to Done."""
        # Create task file in Done (simulating it was moved)
        task_file_name = "task.md"
        (temp_vault / "Done" / task_file_name).write_text("Done task")

        strategy = FileMovementCompletion()
        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=f"Needs_Action/{task_file_name}",
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )

        assert strategy.is_complete("", state, temp_vault)

    def test_no_task_file(self, temp_vault):
        """Test when no task file is specified."""
        strategy = FileMovementCompletion()
        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )

        assert not strategy.is_complete("", state, temp_vault)

    def test_needs_action_empty(self, temp_vault):
        """Test when Needs_Action folder is empty."""
        strategy = FileMovementCompletion()
        state = LoopState(
            loop_id="test",
            prompt="",
            task_file="Needs_Action/task.md",
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )

        # Needs_Action is empty (no .md files)
        assert strategy.is_complete("", state, temp_vault)


class TestCustomCompletion:
    """Test CustomCompletion strategy."""

    def test_callback_returns_true(self, temp_vault):
        """Test when callback returns True."""
        callback = Mock(return_value=True)
        strategy = CustomCompletion(callback)

        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )

        assert strategy.is_complete("output", state, temp_vault)
        callback.assert_called_once_with("output", state, temp_vault)

    def test_callback_returns_false(self, temp_vault):
        """Test when callback returns False."""
        callback = Mock(return_value=False)
        strategy = CustomCompletion(callback)

        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )

        assert not strategy.is_complete("output", state, temp_vault)

    def test_callback_error_handling(self, temp_vault):
        """Test that callback errors are handled gracefully."""
        callback = Mock(side_effect=Exception("Test error"))
        strategy = CustomCompletion(callback)

        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )

        # Should not raise, should return False
        assert not strategy.is_complete("output", state, temp_vault)

    def test_custom_name(self, temp_vault):
        """Test custom strategy name."""
        strategy = CustomCompletion(lambda o, s, p: True, name="MyStrategy")
        assert strategy.name == "MyStrategy"


class TestCompositeCompletion:
    """Test CompositeCompletion strategy."""

    def test_any_strategy_complete(self, temp_vault):
        """Test that completion is detected if any strategy returns True."""
        strategy1 = Mock(spec=CompletionStrategy)
        strategy1.is_complete.return_value = False
        strategy1.name = "Strategy1"

        strategy2 = Mock(spec=CompletionStrategy)
        strategy2.is_complete.return_value = True
        strategy2.name = "Strategy2"

        composite = CompositeCompletion([strategy1, strategy2])

        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )

        assert composite.is_complete("output", state, temp_vault)

    def test_no_strategy_complete(self, temp_vault):
        """Test that completion is not detected if all strategies return False."""
        strategy1 = Mock(spec=CompletionStrategy)
        strategy1.is_complete.return_value = False
        strategy1.name = "Strategy1"

        strategy2 = Mock(spec=CompletionStrategy)
        strategy2.is_complete.return_value = False
        strategy2.name = "Strategy2"

        composite = CompositeCompletion([strategy1, strategy2])

        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )

        assert not composite.is_complete("output", state, temp_vault)

    def test_strategy_error_handling(self, temp_vault):
        """Test that strategy errors are handled gracefully."""
        strategy1 = Mock(spec=CompletionStrategy)
        strategy1.is_complete.side_effect = Exception("Error")
        strategy1.name = "ErrorStrategy"

        strategy2 = Mock(spec=CompletionStrategy)
        strategy2.is_complete.return_value = True
        strategy2.name = "GoodStrategy"

        composite = CompositeCompletion([strategy1, strategy2])

        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )

        # Should continue to strategy2 and return True
        assert composite.is_complete("output", state, temp_vault)


class TestRalphWiggumLoop:
    """Test RalphWiggumLoop class."""

    def test_initialization(self, temp_vault):
        """Test loop initialization."""
        loop = RalphWiggumLoop(str(temp_vault))

        assert loop.vault_path == temp_vault
        assert loop.config.max_iterations == 10
        assert (temp_vault / ".ralph_states").exists()

    def test_custom_config(self, temp_vault):
        """Test initialization with custom config."""
        config = LoopConfig(max_iterations=5, timeout_seconds=120)
        loop = RalphWiggumLoop(str(temp_vault), config=config)

        assert loop.config.max_iterations == 5
        assert loop.config.timeout_seconds == 120

    def test_custom_completion_strategies(self, temp_vault):
        """Test initialization with custom completion strategies."""
        custom_strategy = PromiseCompletion("DONE")
        loop = RalphWiggumLoop(
            str(temp_vault),
            completion_strategies=[custom_strategy]
        )

        # Verify the composite contains our strategy
        assert isinstance(loop.completion_checker, CompositeCompletion)

    def test_state_persistence(self, temp_vault):
        """Test that state is saved and loaded correctly."""
        loop = RalphWiggumLoop(str(temp_vault))

        state = LoopState(
            loop_id="test_persist",
            prompt="Test prompt",
            task_file=None,
            completion_promise="TASK_COMPLETE",
            started=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            iterations=3,
            status="running",
            outputs=[{"iteration": 1, "output": "test"}]
        )

        loop._save_state(state)
        loaded = loop._load_state("test_persist")

        assert loaded is not None
        assert loaded.loop_id == "test_persist"
        assert loaded.iterations == 3
        assert len(loaded.outputs) == 1

    def test_load_nonexistent_state(self, temp_vault):
        """Test loading a state that doesn't exist."""
        loop = RalphWiggumLoop(str(temp_vault))

        result = loop._load_state("nonexistent_id")
        assert result is None

    def test_build_evolved_prompt_first_iteration(self, temp_vault):
        """Test prompt building on first iteration."""
        loop = RalphWiggumLoop(str(temp_vault))

        state = LoopState(
            loop_id="test",
            prompt="Original prompt",
            task_file=None,
            completion_promise="TASK_COMPLETE",
            started="",
            last_updated="",
            iterations=1,
            status="running",
            outputs=[]
        )

        prompt = loop._build_evolved_prompt("Original prompt", state)
        assert prompt == "Original prompt"  # No context on first iteration

    def test_build_evolved_prompt_with_context(self, temp_vault):
        """Test prompt building with previous iteration context."""
        loop = RalphWiggumLoop(str(temp_vault))

        state = LoopState(
            loop_id="test",
            prompt="Original prompt",
            task_file=None,
            completion_promise="TASK_COMPLETE",
            started="",
            last_updated="",
            iterations=2,
            status="running",
            outputs=[
                {"iteration": 1, "output": "First iteration output"}
            ]
        )

        prompt = loop._build_evolved_prompt("Original prompt", state)

        assert "Original prompt" in prompt
        assert "First iteration output" in prompt
        assert "Previous Iterations Context" in prompt
        assert "TASK_COMPLETE" in prompt

    def test_check_requires_approval(self, temp_vault):
        """Test detection of approval requirement in output."""
        loop = RalphWiggumLoop(str(temp_vault))

        assert loop._check_requires_approval("REQUIRES_APPROVAL: Send email")
        assert loop._check_requires_approval("Action NEEDS_HUMAN_REVIEW")
        assert loop._check_requires_approval("PENDING_APPROVAL for payment")
        assert not loop._check_requires_approval("Task completed normally")

    def test_get_active_loops(self, temp_vault):
        """Test getting active loops."""
        loop = RalphWiggumLoop(str(temp_vault))

        # Create some states
        running_state = LoopState(
            loop_id="running_loop",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )
        loop._save_state(running_state)

        completed_state = LoopState(
            loop_id="completed_loop",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=5,
            status="completed"
        )
        loop._save_state(completed_state)

        active = loop.get_active_loops()

        assert len(active) == 1
        assert active[0].loop_id == "running_loop"

    @patch('subprocess.run')
    def test_run_claude_success(self, mock_run, temp_vault):
        """Test successful Claude subprocess execution."""
        mock_run.return_value = MagicMock(
            stdout="Claude output",
            stderr="",
            returncode=0
        )

        loop = RalphWiggumLoop(str(temp_vault))
        result = loop._run_claude("Test prompt", 1)

        assert result.output == "Claude output"
        assert result.exit_code == 0
        assert result.error is None
        assert not result.timed_out

    @patch('subprocess.run')
    def test_run_claude_timeout(self, mock_run, temp_vault):
        """Test Claude subprocess timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=300)

        config = LoopConfig(timeout_seconds=300)
        loop = RalphWiggumLoop(str(temp_vault), config=config)
        result = loop._run_claude("Test prompt", 1)

        assert result.timed_out
        assert "Timeout" in result.error

    @patch('subprocess.run')
    def test_run_claude_error(self, mock_run, temp_vault):
        """Test Claude subprocess error."""
        mock_run.side_effect = Exception("Test error")

        loop = RalphWiggumLoop(str(temp_vault))
        result = loop._run_claude("Test prompt", 1)

        assert result.error == "Test error"
        assert result.exit_code == -1

    def test_log_event(self, temp_vault):
        """Test that events are logged correctly."""
        loop = RalphWiggumLoop(str(temp_vault))

        loop._log_event('test_event', {'key': 'value'})

        today = datetime.now().strftime('%Y-%m-%d')
        log_file = temp_vault / 'Logs' / f'{today}.json'

        assert log_file.exists()

        logs = json.loads(log_file.read_text())
        assert len(logs) > 0

        last_log = logs[-1]
        assert last_log['event'] == 'test_event'
        assert last_log['details']['key'] == 'value'
        assert last_log['component'] == 'RalphWiggumLoop'


class TestRalphWiggumLoopIntegration:
    """Integration tests for the reasoning loop."""

    @patch('subprocess.run')
    def test_start_loop_completes_on_first_try(self, mock_run, temp_vault):
        """Test loop that completes on first iteration."""
        mock_run.return_value = MagicMock(
            stdout="Task done! TASK_COMPLETE",
            stderr="",
            returncode=0
        )

        config = LoopConfig(cooldown_seconds=0)  # No cooldown for tests
        loop = RalphWiggumLoop(str(temp_vault), config=config)

        result = loop.start_loop("Test task")

        assert result.status == 'completed'
        assert result.iterations == 1
        assert len(result.outputs) == 1

    @patch('subprocess.run')
    def test_start_loop_reaches_max_iterations(self, mock_run, temp_vault):
        """Test loop that reaches max iterations without completion."""
        mock_run.return_value = MagicMock(
            stdout="Still working...",
            stderr="",
            returncode=0
        )

        config = LoopConfig(max_iterations=3, cooldown_seconds=0)
        loop = RalphWiggumLoop(str(temp_vault), config=config)

        result = loop.start_loop("Endless task")

        assert result.status == 'max_iterations'
        assert result.iterations == 3

    @patch('subprocess.run')
    def test_start_loop_stops_on_error(self, mock_run, temp_vault):
        """Test loop that stops on error."""
        mock_run.side_effect = Exception("Claude crashed")

        config = LoopConfig(cooldown_seconds=0)
        loop = RalphWiggumLoop(str(temp_vault), config=config)

        result = loop.start_loop("Error task")

        assert result.status == 'error'
        assert "Claude crashed" in result.error
        assert result.iterations == 1

    @patch('subprocess.run')
    def test_start_loop_with_task_file(self, mock_run, temp_vault):
        """Test loop with task file tracking."""
        mock_run.return_value = MagicMock(
            stdout="TASK_COMPLETE",
            stderr="",
            returncode=0
        )

        # Create task file
        task_file = temp_vault / "Needs_Action" / "test_task.md"
        task_file.write_text("Test task content")

        config = LoopConfig(cooldown_seconds=0)
        loop = RalphWiggumLoop(str(temp_vault), config=config)

        result = loop.start_loop(
            prompt="Process this task",
            task_file=task_file
        )

        assert result.task_file == str(task_file)
        assert result.status == 'completed'

    @patch('subprocess.run')
    def test_resume_loop(self, mock_run, temp_vault):
        """Test resuming an interrupted loop."""
        mock_run.return_value = MagicMock(
            stdout="TASK_COMPLETE",
            stderr="",
            returncode=0
        )

        # Create a state to resume
        loop = RalphWiggumLoop(str(temp_vault), config=LoopConfig(cooldown_seconds=0))

        initial_state = LoopState(
            loop_id="resume_test",
            prompt="Test prompt",
            task_file=None,
            completion_promise="TASK_COMPLETE",
            started=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            iterations=2,
            status="running",
            outputs=[
                {"iteration": 1, "output": "First"},
                {"iteration": 2, "output": "Second"}
            ]
        )
        loop._save_state(initial_state)

        # Resume
        result = loop.resume_loop("resume_test")

        assert result is not None
        assert result.status == 'completed'
        assert result.iterations == 3  # Continued from 2

    def test_resume_nonexistent_loop(self, temp_vault):
        """Test resuming a loop that doesn't exist."""
        loop = RalphWiggumLoop(str(temp_vault))

        result = loop.resume_loop("nonexistent")

        assert result is None

    def test_resume_completed_loop(self, temp_vault):
        """Test resuming an already completed loop."""
        loop = RalphWiggumLoop(str(temp_vault))

        completed_state = LoopState(
            loop_id="completed_test",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=5,
            status="completed"
        )
        loop._save_state(completed_state)

        result = loop.resume_loop("completed_test")

        # Should return the state but not continue
        assert result is not None
        assert result.status == 'completed'
        assert result.iterations == 5


class TestIterationResult:
    """Test IterationResult dataclass."""

    def test_creation(self):
        """Test creating an iteration result."""
        result = IterationResult(
            iteration=1,
            started="2026-01-20T10:00:00",
            completed="2026-01-20T10:01:00",
            duration_seconds=60.0,
            output="Test output",
            output_truncated=False,
            exit_code=0
        )

        assert result.iteration == 1
        assert result.duration_seconds == 60.0
        assert result.exit_code == 0
        assert not result.timed_out
        assert result.error is None

    def test_with_error(self):
        """Test iteration result with error."""
        result = IterationResult(
            iteration=1,
            started="",
            completed="",
            duration_seconds=5.0,
            output="",
            output_truncated=False,
            exit_code=-1,
            error="Test error",
            timed_out=True
        )

        assert result.error == "Test error"
        assert result.timed_out


class TestHITLIntegration:
    """Test HITL (Human-in-the-Loop) integration in Ralph Wiggum Loop."""

    def test_config_hitl_enabled_by_default(self):
        """Test that HITL is enabled by default in config."""
        config = LoopConfig()
        assert config.enable_hitl is True
        assert config.approval_timeout_hours == 24
        assert config.approval_check_interval == 5

    def test_config_hitl_disabled(self):
        """Test disabling HITL in config."""
        config = LoopConfig(enable_hitl=False)
        assert config.enable_hitl is False

    def test_loop_state_approval_fields(self):
        """Test LoopState has approval tracking fields."""
        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="waiting_approval",
            approval_request="/path/to/approval.md",
            approval_action_type="send_email",
            approval_details={"to": "test@example.com"},
            approval_reason="External recipient"
        )

        assert state.approval_request == "/path/to/approval.md"
        assert state.approval_action_type == "send_email"
        assert state.approval_details["to"] == "test@example.com"
        assert state.approval_reason == "External recipient"

    def test_loop_state_serialization_with_approval(self):
        """Test LoopState serialization includes approval fields."""
        state = LoopState(
            loop_id="test",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="waiting_approval",
            approval_request="/path/to/approval.md",
            approval_action_type="payment",
            approval_details={"amount": 500},
            approval_reason="Large payment"
        )

        data = state.to_dict()
        assert data['approval_request'] == "/path/to/approval.md"
        assert data['approval_action_type'] == "payment"
        assert data['approval_details']['amount'] == 500

    def test_extract_approval_no_approval_needed(self, temp_vault):
        """Test extraction returns None when no approval needed."""
        loop = RalphWiggumLoop(str(temp_vault))

        result = loop._extract_approval_request("Task completed successfully!")
        assert result is None

    def test_extract_approval_basic(self, temp_vault):
        """Test extraction of basic approval request."""
        loop = RalphWiggumLoop(str(temp_vault))

        output = """
I need to send an email.

REQUIRES_APPROVAL: send_email

Action: send_email
Reason: External recipient requires review

```json
{"to": "client@example.com", "subject": "Invoice"}
```
"""
        result = loop._extract_approval_request(output)

        assert result is not None
        action_type, details, reason = result
        assert action_type == "send_email"
        assert details.get("to") == "client@example.com"
        assert "External" in reason or "review" in reason.lower()

    def test_extract_approval_payment(self, temp_vault):
        """Test extraction of payment approval request."""
        loop = RalphWiggumLoop(str(temp_vault))

        output = """
Processing payment request.

REQUIRES_APPROVAL: payment

Action: payment
Amount: $500.00
Reason: Large payment requires authorization

```json
{"amount": 500, "recipient": "vendor@example.com"}
```
"""
        result = loop._extract_approval_request(output)

        assert result is not None
        action_type, details, _ = result
        assert action_type == "payment"

    def test_extract_approval_infer_action_type(self, temp_vault):
        """Test that action type is inferred from content."""
        loop = RalphWiggumLoop(str(temp_vault))

        # Email inference
        output1 = "REQUIRES_APPROVAL - Need to send email to external address"
        result1 = loop._extract_approval_request(output1)
        assert result1 is not None
        assert result1[0] == "send_email"

        # Payment inference
        output2 = "REQUIRES_APPROVAL - Process payment of $200"
        result2 = loop._extract_approval_request(output2)
        assert result2 is not None
        assert result2[0] == "payment"

        # Social post inference
        output3 = "REQUIRES_APPROVAL - Post to LinkedIn"
        result3 = loop._extract_approval_request(output3)
        assert result3 is not None
        assert result3[0] == "post_social"

    def test_get_loops_waiting_approval(self, temp_vault):
        """Test getting loops waiting for approval."""
        loop = RalphWiggumLoop(str(temp_vault))

        # Create waiting state
        waiting_state = LoopState(
            loop_id="waiting_loop",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="waiting_approval",
            approval_request="/path/to/approval.md"
        )
        loop._save_state(waiting_state)

        # Create running state
        running_state = LoopState(
            loop_id="running_loop",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )
        loop._save_state(running_state)

        waiting = loop.get_loops_waiting_approval()

        assert len(waiting) == 1
        assert waiting[0].loop_id == "waiting_loop"
        assert waiting[0].status == "waiting_approval"

    def test_notify_approval_granted(self, temp_vault):
        """Test notifying loop that approval was granted."""
        loop = RalphWiggumLoop(str(temp_vault))

        # Create waiting state
        state = LoopState(
            loop_id="notify_test",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="waiting_approval"
        )
        loop._save_state(state)

        # Notify approval granted
        result = loop.notify_approval("notify_test", approved=True)

        assert result is True

        # Load state and verify
        updated = loop._load_state("notify_test")
        assert updated.status == "running"

    def test_notify_approval_rejected(self, temp_vault):
        """Test notifying loop that approval was rejected."""
        loop = RalphWiggumLoop(str(temp_vault))

        # Create waiting state
        state = LoopState(
            loop_id="reject_test",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="waiting_approval"
        )
        loop._save_state(state)

        # Notify approval rejected
        result = loop.notify_approval("reject_test", approved=False)

        assert result is True

        # Load state and verify
        updated = loop._load_state("reject_test")
        assert updated.status == "rejected"
        assert "rejected" in updated.error.lower()

    def test_notify_approval_nonexistent_loop(self, temp_vault):
        """Test notifying a loop that doesn't exist."""
        loop = RalphWiggumLoop(str(temp_vault))

        result = loop.notify_approval("nonexistent", approved=True)
        assert result is False

    def test_notify_approval_wrong_status(self, temp_vault):
        """Test notifying a loop that isn't waiting for approval."""
        loop = RalphWiggumLoop(str(temp_vault))

        # Create running state (not waiting)
        state = LoopState(
            loop_id="running_test",
            prompt="",
            task_file=None,
            completion_promise="",
            started="",
            last_updated="",
            iterations=1,
            status="running"
        )
        loop._save_state(state)

        result = loop.notify_approval("running_test", approved=True)
        assert result is False

    def test_approval_manager_initialized(self, temp_vault):
        """Test that ApprovalManager is initialized when HITL enabled."""
        config = LoopConfig(enable_hitl=True)
        loop = RalphWiggumLoop(str(temp_vault), config=config)

        assert loop.approval_manager is not None

    def test_approval_manager_not_initialized_when_disabled(self, temp_vault):
        """Test that ApprovalManager is not initialized when HITL disabled."""
        config = LoopConfig(enable_hitl=False)
        loop = RalphWiggumLoop(str(temp_vault), config=config)

        assert loop.approval_manager is None

    def test_evolved_prompt_includes_approval_instructions(self, temp_vault):
        """Test that evolved prompt includes approval request format."""
        loop = RalphWiggumLoop(str(temp_vault))

        state = LoopState(
            loop_id="test",
            prompt="Original prompt",
            task_file=None,
            completion_promise="TASK_COMPLETE",
            started="",
            last_updated="",
            iterations=2,
            status="running",
            outputs=[{"iteration": 1, "output": "First output"}]
        )

        prompt = loop._build_evolved_prompt("Original prompt", state)

        assert "REQUIRES_APPROVAL" in prompt
        assert "send_email" in prompt or "payment" in prompt
        assert "json" in prompt.lower()


class TestHITLApprovalWorkflow:
    """Test the full HITL approval workflow."""

    @patch('subprocess.run')
    def test_loop_pauses_on_approval_request(self, mock_run, temp_vault):
        """Test that loop pauses when approval is requested."""
        # First call triggers approval, second completes
        mock_run.side_effect = [
            MagicMock(
                stdout="REQUIRES_APPROVAL: send_email\n\nAction: send_email\nReason: External recipient",
                stderr="",
                returncode=0
            ),
            MagicMock(
                stdout="TASK_COMPLETE",
                stderr="",
                returncode=0
            )
        ]

        # Mock the approval waiting to return immediately (approved)
        config = LoopConfig(
            cooldown_seconds=0,
            enable_hitl=True,
            approval_check_interval=0
        )
        loop = RalphWiggumLoop(str(temp_vault), config=config)

        # Mock the wait_for_approval to return True immediately
        with patch.object(loop, '_wait_for_approval', return_value=True):
            result = loop.start_loop("Test email task")

        # Should have paused, gotten approval, and completed
        assert result.status == 'completed'
        assert result.iterations >= 1

    @patch('subprocess.run')
    def test_loop_stops_on_rejection(self, mock_run, temp_vault):
        """Test that loop stops when approval is rejected."""
        mock_run.return_value = MagicMock(
            stdout="REQUIRES_APPROVAL: payment\n\nAction: payment",
            stderr="",
            returncode=0
        )

        config = LoopConfig(
            cooldown_seconds=0,
            enable_hitl=True,
            approval_check_interval=0
        )
        loop = RalphWiggumLoop(str(temp_vault), config=config)

        # Mock rejection
        with patch.object(loop, '_wait_for_approval', return_value=False):
            with patch.object(loop, '_is_approval_rejected', return_value=True):
                result = loop.start_loop("Test payment task")

        assert result.status == 'rejected'
        assert "rejected" in result.error.lower()

    @patch('subprocess.run')
    def test_loop_handles_approval_timeout(self, mock_run, temp_vault):
        """Test that loop handles approval timeout."""
        mock_run.return_value = MagicMock(
            stdout="REQUIRES_APPROVAL: unknown\n\nAction needed",
            stderr="",
            returncode=0
        )

        config = LoopConfig(
            cooldown_seconds=0,
            enable_hitl=True,
            approval_check_interval=0
        )
        loop = RalphWiggumLoop(str(temp_vault), config=config)

        # Mock timeout (not rejected, just timed out)
        with patch.object(loop, '_wait_for_approval', return_value=False):
            with patch.object(loop, '_is_approval_rejected', return_value=False):
                result = loop.start_loop("Test timeout task")

        assert result.status == 'approval_timeout'
        assert "timed out" in result.error.lower()
