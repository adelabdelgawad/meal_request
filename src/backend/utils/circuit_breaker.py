"""
Circuit Breaker Implementation for AD Authentication

Prevents cascading failures when AD is down by failing fast after detecting
consistent failures. Opens the circuit after threshold failures, preventing
unnecessary blocking calls to unavailable AD.

Based on the Circuit Breaker pattern from Michael Nygard's "Release It!".
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Circuit open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5
    """Number of failures before opening circuit."""

    success_threshold: int = 2
    """Number of successes in half-open to close circuit."""

    timeout_seconds: float = 30.0
    """Seconds to wait before attempting recovery (half-open)."""

    window_seconds: float = 60.0
    """Time window for counting failures."""


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring."""

    failure_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    opened_at: Optional[float] = None
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0


class CircuitBreakerError(Exception):
    """Raised when circuit is open and request is rejected."""
    pass


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    Usage:
        breaker = CircuitBreaker("ad_auth", config)

        try:
            result = await breaker.call(async_func, *args, **kwargs)
        except CircuitBreakerError:
            # Circuit is open, fail fast
            return fallback_value
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()

        logger.info(
            f"Circuit breaker '{name}' initialized: "
            f"failure_threshold={self.config.failure_threshold}, "
            f"timeout={self.config.timeout_seconds}s"
        )

    async def call(
        self,
        func: Callable,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Async or sync callable to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            CircuitBreakerError: If circuit is open
            Exception: Any exception from func (also triggers failure)
        """
        async with self._lock:
            self.metrics.total_calls += 1

            # Check if circuit should transition states
            await self._check_state_transition()

            # If circuit is open, fail fast
            if self.state == CircuitState.OPEN:
                logger.warning(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Rejecting call (fast fail). "
                    f"Opened at: {self.metrics.opened_at}"
                )
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is open. Service unavailable."
                )

        # Execute the function
        try:
            # Call function (handles both async and sync)
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Record success
            await self._on_success()
            return result

        except Exception as e:
            # Record failure
            await self._on_failure(e)
            raise

    async def _check_state_transition(self):
        """Check if circuit should transition to a different state."""
        now = time.time()

        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if (self.metrics.opened_at and
                now - self.metrics.opened_at >= self.config.timeout_seconds):
                logger.info(
                    f"Circuit breaker '{self.name}' transitioning: "
                    f"OPEN → HALF_OPEN (timeout elapsed)"
                )
                self.state = CircuitState.HALF_OPEN
                self.metrics.consecutive_successes = 0

    async def _on_success(self):
        """Handle successful call."""
        async with self._lock:
            now = time.time()
            self.metrics.total_successes += 1
            self.metrics.last_success_time = now
            self.metrics.consecutive_failures = 0
            self.metrics.consecutive_successes += 1

            # If in half-open state, check if we can close
            if self.state == CircuitState.HALF_OPEN:
                if self.metrics.consecutive_successes >= self.config.success_threshold:
                    logger.info(
                        f"Circuit breaker '{self.name}' transitioning: "
                        f"HALF_OPEN → CLOSED (success threshold reached)"
                    )
                    self.state = CircuitState.CLOSED
                    self.metrics.consecutive_failures = 0
                    self.metrics.opened_at = None

    async def _on_failure(self, error: Exception):
        """Handle failed call."""
        async with self._lock:
            now = time.time()
            self.metrics.total_failures += 1
            self.metrics.last_failure_time = now
            self.metrics.consecutive_successes = 0
            self.metrics.consecutive_failures += 1

            # Log failure
            logger.warning(
                f"Circuit breaker '{self.name}' recorded failure "
                f"({self.metrics.consecutive_failures}/{self.config.failure_threshold}): "
                f"{type(error).__name__}: {str(error)[:100]}"
            )

            # Check if we should open the circuit
            if self.state == CircuitState.CLOSED:
                if self.metrics.consecutive_failures >= self.config.failure_threshold:
                    logger.error(
                        f"Circuit breaker '{self.name}' transitioning: "
                        f"CLOSED → OPEN (failure threshold reached: "
                        f"{self.metrics.consecutive_failures} consecutive failures)"
                    )
                    self.state = CircuitState.OPEN
                    self.metrics.opened_at = now

            elif self.state == CircuitState.HALF_OPEN:
                # Single failure in half-open reopens circuit
                logger.warning(
                    f"Circuit breaker '{self.name}' transitioning: "
                    f"HALF_OPEN → OPEN (failure during recovery test)"
                )
                self.state = CircuitState.OPEN
                self.metrics.opened_at = now

    def get_state(self) -> dict:
        """Get current circuit breaker state and metrics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "metrics": {
                "total_calls": self.metrics.total_calls,
                "total_successes": self.metrics.total_successes,
                "total_failures": self.metrics.total_failures,
                "consecutive_failures": self.metrics.consecutive_failures,
                "consecutive_successes": self.metrics.consecutive_successes,
                "last_failure_time": self.metrics.last_failure_time,
                "last_success_time": self.metrics.last_success_time,
                "opened_at": self.metrics.opened_at,
            },
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout_seconds": self.config.timeout_seconds,
            }
        }

    async def reset(self):
        """Reset circuit breaker to closed state (for testing/admin use)."""
        async with self._lock:
            logger.info(f"Circuit breaker '{self.name}' manually reset to CLOSED")
            self.state = CircuitState.CLOSED
            self.metrics = CircuitBreakerMetrics()
