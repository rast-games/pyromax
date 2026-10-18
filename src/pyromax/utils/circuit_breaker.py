from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from ..exceptions import CircuitBreakerOpenError


class CircuitBreakerState(str, Enum):
    """Possible states of a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(frozen=True, slots=True)
class _CircuitBreakerPermit:
    generation: int
    probe: bool = False


class CircuitBreaker:
    """Async circuit breaker for logical operations.

    Failures are counted consecutively. Once ``failure_threshold`` is reached,
    calls fail fast until ``recovery_timeout`` has elapsed. Exactly one call is
    then admitted as a half-open probe. Failed probes increase the recovery
    timeout by ``backoff_factor`` up to ``max_recovery_timeout``.
    """

    def __init__(
        self,
        failure_threshold: int = 1,
        recovery_timeout: float = 1.0,
        *,
        max_cycles: int = 5,
        backoff_factor: float = 2.0,
        max_recovery_timeout: float = 30.0,
        wait_when_open: bool = True,
        name: str | None = None,
        time_func: Callable[[], float] = time.monotonic,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if recovery_timeout < 0:
            raise ValueError("recovery_timeout cannot be negative")
        if max_cycles < 0:
            raise ValueError("max_cycles cannot be negative")
        if backoff_factor < 1:
            raise ValueError("backoff_factor must be at least 1")
        if max_recovery_timeout < recovery_timeout:
            raise ValueError(
                "max_recovery_timeout cannot be less than recovery_timeout"
            )

        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.max_cycles = max_cycles
        self.backoff_factor = backoff_factor
        self.max_recovery_timeout = max_recovery_timeout
        self.wait_when_open = wait_when_open
        self.name = name
        self._time = time_func
        self._current_recovery_timeout = recovery_timeout
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None
        self._generation = 0
        self._lock = asyncio.Lock()
        self._state_changed = asyncio.Event()

    @property
    def state(self) -> CircuitBreakerState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def retry_after(self) -> float:
        """Return seconds before another probe may be attempted."""
        if self._state is CircuitBreakerState.CLOSED:
            return 0.0
        if self._state is CircuitBreakerState.HALF_OPEN:
            return 0.0
        if self._opened_at is None:
            return self._current_recovery_timeout
        return max(
            0.0,
            self._current_recovery_timeout - (self._time() - self._opened_at),
        )

    async def before_call(self) -> _CircuitBreakerPermit:
        """Admit a call or raise when the circuit is not ready."""
        async with self._lock:
            if self._state is CircuitBreakerState.CLOSED:
                return _CircuitBreakerPermit(self._generation)

            if self._state is CircuitBreakerState.OPEN and self.retry_after <= 0:
                self._state = CircuitBreakerState.HALF_OPEN
                self._notify_state_changed()
                return _CircuitBreakerPermit(self._generation, probe=True)

            raise CircuitBreakerOpenError(self.retry_after, circuit=self.name)

    async def wait_for_call(self) -> _CircuitBreakerPermit:
        """Wait for the cooldown and acquire the next available call permit."""
        while True:
            async with self._lock:
                if self._state is CircuitBreakerState.CLOSED:
                    return _CircuitBreakerPermit(self._generation)

                retry_after = self.retry_after
                if self._state is CircuitBreakerState.OPEN and retry_after <= 0:
                    self._state = CircuitBreakerState.HALF_OPEN
                    self._notify_state_changed()
                    return _CircuitBreakerPermit(self._generation, probe=True)

                state_changed = self._state_changed
                wait_timeout = (
                    retry_after
                    if self._state is CircuitBreakerState.OPEN
                    else None
                )

            if wait_timeout is None:
                await state_changed.wait()
                continue
            try:
                await asyncio.wait_for(state_changed.wait(), timeout=wait_timeout)
            except asyncio.TimeoutError:
                pass

    async def wait_until_available(self) -> None:
        """Wait until a call may attempt to acquire the circuit."""
        while True:
            async with self._lock:
                if self._state is CircuitBreakerState.CLOSED:
                    return

                retry_after = self.retry_after
                if self._state is CircuitBreakerState.OPEN and retry_after <= 0:
                    return

                state_changed = self._state_changed
                wait_timeout = (
                    retry_after
                    if self._state is CircuitBreakerState.OPEN
                    else None
                )

            if wait_timeout is None:
                await state_changed.wait()
                continue
            try:
                await asyncio.wait_for(state_changed.wait(), timeout=wait_timeout)
            except asyncio.TimeoutError:
                pass

    async def record_success(self, permit: _CircuitBreakerPermit) -> None:
        """Record a successful admitted call."""
        async with self._lock:
            if permit.generation != self._generation:
                return

            if permit.probe:
                if self._state is not CircuitBreakerState.HALF_OPEN:
                    return
                self._state = CircuitBreakerState.CLOSED
                self._opened_at = None
                self._current_recovery_timeout = self.recovery_timeout
                self._generation += 1
                self._notify_state_changed()

            if self._state is CircuitBreakerState.CLOSED:
                self._failure_count = 0

    async def record_failure(self, permit: _CircuitBreakerPermit) -> None:
        """Record a dependency failure for an admitted call."""
        async with self._lock:
            if permit.generation != self._generation:
                return

            if permit.probe:
                if self._state is CircuitBreakerState.HALF_OPEN:
                    self._open(increase_timeout=True)
                return

            if self._state is not CircuitBreakerState.CLOSED:
                return

            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._open(increase_timeout=False)

    async def record_ignored(self, permit: _CircuitBreakerPermit) -> None:
        """Release a cancelled half-open probe without counting a failure."""
        async with self._lock:
            if permit.generation != self._generation or not permit.probe:
                return
            if self._state is CircuitBreakerState.HALF_OPEN:
                self._state = CircuitBreakerState.OPEN
                self._generation += 1
                self._notify_state_changed()

    async def reset(self) -> None:
        """Close the circuit and clear its failure history."""
        async with self._lock:
            self._state = CircuitBreakerState.CLOSED
            self._failure_count = 0
            self._opened_at = None
            self._current_recovery_timeout = self.recovery_timeout
            self._generation += 1
            self._notify_state_changed()

    def _open(self, *, increase_timeout: bool) -> None:
        if increase_timeout:
            self._current_recovery_timeout = min(
                self._current_recovery_timeout * self.backoff_factor,
                self.max_recovery_timeout,
            )
        else:
            self._current_recovery_timeout = self.recovery_timeout
        self._state = CircuitBreakerState.OPEN
        self._opened_at = self._time()
        self._generation += 1
        self._notify_state_changed()

    def _notify_state_changed(self) -> None:
        state_changed = self._state_changed
        self._state_changed = asyncio.Event()
        state_changed.set()


__all__ = ["CircuitBreaker", "CircuitBreakerState"]
