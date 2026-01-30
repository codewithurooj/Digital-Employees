"""
Utilities Package - Shared utilities for the AI Employee system.

Provides:
- retry_handler: Retry logic with exponential backoff and circuit breakers
- hitl: Human-in-the-Loop approval workflow management
- ralph_wiggum: Claude Reasoning Loop for persistent task completion
"""

from .retry_handler import (
    retry,
    RetryConfig,
    RetryError,
    CircuitBreaker,
    CircuitOpenError,
    RateLimiter,
    get_rate_limiter
)

from .hitl import (
    ApprovalManager,
    ApprovalWatcher,
    ApprovalStatus,
    require_approval,
    check_approval
)

from .ralph_wiggum import (
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

from .audit_logger import AuditLogger, AuditEntry

__all__ = [
    # Retry handler
    'retry',
    'RetryConfig',
    'RetryError',
    'CircuitBreaker',
    'CircuitOpenError',
    'RateLimiter',
    'get_rate_limiter',
    # HITL
    'ApprovalManager',
    'ApprovalWatcher',
    'ApprovalStatus',
    'require_approval',
    'check_approval',
    # Ralph Wiggum (Reasoning Loop)
    'RalphWiggumLoop',
    'LoopConfig',
    'LoopState',
    'IterationResult',
    'CompletionStrategy',
    'PromiseCompletion',
    'FileMovementCompletion',
    'CustomCompletion',
    'CompositeCompletion',
    # Audit Logger
    'AuditLogger',
    'AuditEntry',
]
