"""
Retry Handler with Exponential Backoff

Provides robust retry logic for external API calls and operations
that may fail transiently.

Usage:
    from src.utils.retry_handler import retry, RetryConfig, CircuitBreaker

    # Simple retry with decorator
    @retry(max_attempts=3, backoff_factor=2)
    def call_external_api():
        return requests.get('https://api.example.com/data')

    # With circuit breaker
    breaker = CircuitBreaker('gmail_api', failure_threshold=5)

    @breaker.protect
    @retry(max_attempts=3)
    def send_email():
        # API call here
        pass
"""

import time
import random
import logging
import functools
from typing import Callable, Any, Optional, Tuple, Type, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    backoff_factor: float = 2.0
    initial_delay: float = 1.0
    max_delay: float = 60.0
    jitter: bool = True
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = ()


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 60
    half_open_max_calls: int = 3


class RetryError(Exception):
    """Raised when all retry attempts are exhausted."""
    def __init__(self, message: str, last_exception: Exception, attempts: int):
        super().__init__(message)
        self.last_exception = last_exception
        self.attempts = attempts


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    def __init__(self, name: str, time_until_retry: float):
        super().__init__(f"Circuit '{name}' is open. Retry in {time_until_retry:.1f}s")
        self.name = name
        self.time_until_retry = time_until_retry


def calculate_delay(
    attempt: int,
    config: RetryConfig
) -> float:
    """
    Calculate delay for next retry attempt.

    Uses exponential backoff with optional jitter.
    """
    delay = config.initial_delay * (config.backoff_factor ** (attempt - 1))
    delay = min(delay, config.max_delay)

    if config.jitter:
        # Add random jitter (0-25% of delay)
        delay = delay * (1 + random.random() * 0.25)

    return delay


def retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    non_retryable_exceptions: Tuple[Type[Exception], ...] = (),
    on_retry: Optional[Callable[[int, Exception], None]] = None
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        backoff_factor: Multiplier for delay between attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between attempts
        jitter: Add random jitter to delays
        retryable_exceptions: Exceptions that trigger retry
        non_retryable_exceptions: Exceptions that should not be retried
        on_retry: Callback function called on each retry

    Example:
        @retry(max_attempts=3, backoff_factor=2)
        def fetch_data():
            return api.get_data()
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        backoff_factor=backoff_factor,
        initial_delay=initial_delay,
        max_delay=max_delay,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
        non_retryable_exceptions=non_retryable_exceptions
    )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(f'retry.{func.__name__}')
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except config.non_retryable_exceptions as e:
                    # Don't retry these
                    logger.warning(f"Non-retryable exception: {e}")
                    raise

                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt == config.max_attempts:
                        logger.error(
                            f"All {config.max_attempts} attempts failed for {func.__name__}"
                        )
                        raise RetryError(
                            f"Failed after {config.max_attempts} attempts",
                            last_exception,
                            attempt
                        )

                    delay = calculate_delay(attempt, config)
                    logger.warning(
                        f"Attempt {attempt}/{config.max_attempts} failed: {e}. "
                        f"Retrying in {delay:.1f}s"
                    )

                    if on_retry:
                        on_retry(attempt, e)

                    time.sleep(delay)

        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.

    Prevents cascading failures by temporarily blocking calls to failing services.

    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Service failing, calls rejected immediately
    - HALF_OPEN: Testing if service recovered

    Usage:
        breaker = CircuitBreaker('external_api', failure_threshold=5)

        @breaker.protect
        def call_api():
            return requests.get('https://api.example.com')
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
        on_state_change: Optional[Callable[[str, CircuitState], None]] = None
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Identifier for this circuit
            failure_threshold: Failures before opening circuit
            success_threshold: Successes in half-open to close circuit
            timeout_seconds: Time to wait before half-opening
            on_state_change: Callback when state changes
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.on_state_change = on_state_change

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0

        self.logger = logging.getLogger(f'circuit.{name}')

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for timeout."""
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try resetting."""
        if self._last_failure_time is None:
            return True
        elapsed = (datetime.now() - self._last_failure_time).total_seconds()
        return elapsed >= self.timeout_seconds

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
            self._success_count = 0

        self.logger.info(f"Circuit '{self.name}' state: {old_state.value} -> {new_state.value}")

        if self.on_state_change:
            self.on_state_change(self.name, new_state)

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._transition_to(CircuitState.CLOSED)
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)

    def allow_request(self) -> bool:
        """Check if a request should be allowed."""
        state = self.state  # This may trigger state transition

        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.OPEN:
            return False
        else:  # HALF_OPEN
            self._half_open_calls += 1
            return self._half_open_calls <= 3  # Allow limited test calls

    def time_until_retry(self) -> float:
        """Get seconds until circuit might allow retry."""
        if self._state != CircuitState.OPEN or self._last_failure_time is None:
            return 0

        elapsed = (datetime.now() - self._last_failure_time).total_seconds()
        remaining = self.timeout_seconds - elapsed
        return max(0, remaining)

    def protect(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with this circuit breaker.

        Example:
            @breaker.protect
            def call_api():
                return api.fetch()
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not self.allow_request():
                raise CircuitOpenError(self.name, self.time_until_retry())

            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise

        return wrapper

    def get_status(self) -> dict:
        """Get current circuit breaker status."""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self._failure_count,
            'success_count': self._success_count,
            'time_until_retry': self.time_until_retry()
        }


class RateLimiter:
    """
    Rate limiter to prevent exceeding API limits.

    Usage:
        limiter = RateLimiter('email', max_calls=10, period_seconds=3600)

        if limiter.allow():
            send_email()
        else:
            print(f"Rate limited. Retry in {limiter.time_until_reset()}s")
    """

    def __init__(
        self,
        name: str,
        max_calls: int,
        period_seconds: int = 3600
    ):
        """
        Initialize rate limiter.

        Args:
            name: Identifier for this limiter
            max_calls: Maximum calls per period
            period_seconds: Period duration in seconds
        """
        self.name = name
        self.max_calls = max_calls
        self.period_seconds = period_seconds
        self._calls: List[datetime] = []
        self.logger = logging.getLogger(f'ratelimit.{name}')

    def _cleanup_old_calls(self) -> None:
        """Remove calls outside the current period."""
        cutoff = datetime.now() - timedelta(seconds=self.period_seconds)
        self._calls = [t for t in self._calls if t > cutoff]

    def allow(self) -> bool:
        """Check if a call is allowed and record it if so."""
        self._cleanup_old_calls()

        if len(self._calls) >= self.max_calls:
            self.logger.warning(f"Rate limit reached for '{self.name}'")
            return False

        self._calls.append(datetime.now())
        return True

    def remaining(self) -> int:
        """Get remaining calls in current period."""
        self._cleanup_old_calls()
        return max(0, self.max_calls - len(self._calls))

    def time_until_reset(self) -> float:
        """Get seconds until oldest call expires."""
        self._cleanup_old_calls()

        if not self._calls:
            return 0

        oldest = self._calls[0]
        elapsed = (datetime.now() - oldest).total_seconds()
        return max(0, self.period_seconds - elapsed)

    def get_status(self) -> dict:
        """Get current rate limiter status."""
        self._cleanup_old_calls()
        return {
            'name': self.name,
            'calls_made': len(self._calls),
            'max_calls': self.max_calls,
            'remaining': self.remaining(),
            'time_until_reset': self.time_until_reset()
        }


# Pre-configured rate limiters based on Company Handbook
DEFAULT_RATE_LIMITS = {
    'email': RateLimiter('email', max_calls=10, period_seconds=3600),
    'payment': RateLimiter('payment', max_calls=3, period_seconds=3600),
    'social_post': RateLimiter('social_post', max_calls=5, period_seconds=86400),
}


def get_rate_limiter(name: str) -> RateLimiter:
    """Get a pre-configured rate limiter."""
    return DEFAULT_RATE_LIMITS.get(name, RateLimiter(name, 100, 3600))
