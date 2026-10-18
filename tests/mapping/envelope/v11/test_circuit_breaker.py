import asyncio
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from pyromax.config import (
    CircuitBreakerConfig,
    EnvelopeMapperConfigV11,
    MappingCircuitBreakersConfig,
)
from pyromax.exceptions import (
    CircuitBreakerOpenError,
    MapperApiError,
    MapperTransportError,
)
from pyromax.mapping.envelope.v11.mixins.transport import TransportMixin
from pyromax.mapping.envelope.v11.LifecycleManager import LifecycleManager
from pyromax.mapping.envelope.v11.mixins.auth import AuthMixin
from pyromax.utils import CircuitBreaker, CircuitBreakerState


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class CircuitBreakerTest(unittest.IsolatedAsyncioTestCase):
    async def test_opens_and_recovers_through_one_half_open_probe(self) -> None:
        clock = Clock()
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=10,
            time_func=clock,
        )

        first = await breaker.before_call()
        await breaker.record_failure(first)
        self.assertEqual(breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(breaker.failure_count, 1)

        second = await breaker.before_call()
        await breaker.record_failure(second)
        self.assertEqual(breaker.state, CircuitBreakerState.OPEN)

        with self.assertRaises(CircuitBreakerOpenError) as raised:
            await breaker.before_call()
        self.assertEqual(raised.exception.retry_after, 10)

        clock.advance(10)
        probe = await breaker.before_call()
        self.assertEqual(breaker.state, CircuitBreakerState.HALF_OPEN)
        with self.assertRaises(CircuitBreakerOpenError):
            await breaker.before_call()

        await breaker.record_success(probe)
        self.assertEqual(breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(breaker.failure_count, 0)

    async def test_failed_probe_reopens_with_backoff(self) -> None:
        clock = Clock()
        breaker = CircuitBreaker(1, 5, time_func=clock)
        permit = await breaker.before_call()
        await breaker.record_failure(permit)

        clock.advance(5)
        probe = await breaker.before_call()
        await breaker.record_failure(probe)

        self.assertEqual(breaker.state, CircuitBreakerState.OPEN)
        self.assertEqual(breaker.retry_after, 10)

    async def test_failed_probes_increase_recovery_timeout(self) -> None:
        clock = Clock()
        breaker = CircuitBreaker(
            1,
            1,
            backoff_factor=2,
            max_recovery_timeout=3,
            time_func=clock,
        )
        permit = await breaker.before_call()
        await breaker.record_failure(permit)
        self.assertEqual(breaker.retry_after, 1)

        clock.advance(1)
        probe = await breaker.before_call()
        await breaker.record_failure(probe)
        self.assertEqual(breaker.retry_after, 2)

        clock.advance(2)
        probe = await breaker.before_call()
        await breaker.record_failure(probe)
        self.assertEqual(breaker.retry_after, 3)

    async def test_api_errors_only_trip_api_circuit(self) -> None:
        transport_breaker = CircuitBreaker(
            1, 30, max_cycles=0, name="transport"
        )
        api_breaker = CircuitBreaker(1, 30, max_cycles=0, name="api")

        class Target:
            _transport_circuit_breaker = transport_breaker
            _api_circuit_breaker = api_breaker
            _send_with_retries = AsyncMock(
                side_effect=MapperApiError("request was rejected")
            )

        target = Target()
        with self.assertRaises(MapperApiError):
            await TransportMixin.send(target, object())
        self.assertEqual(transport_breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(api_breaker.state, CircuitBreakerState.OPEN)

        with self.assertRaises(CircuitBreakerOpenError) as raised:
            await api_breaker.before_call()
        self.assertEqual(raised.exception.circuit, "api")
        self.assertEqual(target._send_with_retries.await_count, 1)

    async def test_transport_errors_only_trip_transport_circuit(self) -> None:
        transport_breaker = CircuitBreaker(
            1, 30, max_cycles=0, name="transport"
        )
        api_breaker = CircuitBreaker(1, 30, max_cycles=0, name="api")

        class Target:
            _transport_circuit_breaker = transport_breaker
            _api_circuit_breaker = api_breaker
            _send_with_retries = AsyncMock(
                side_effect=MapperTransportError("offline")
            )

        target = Target()
        with self.assertRaises(MapperTransportError):
            await TransportMixin.send(target, object())
        self.assertEqual(transport_breaker.state, CircuitBreakerState.OPEN)
        self.assertEqual(api_breaker.state, CircuitBreakerState.CLOSED)

        with self.assertRaises(CircuitBreakerOpenError) as raised:
            await transport_breaker.before_call()
        self.assertEqual(raised.exception.circuit, "transport")
        self.assertEqual(target._send_with_retries.await_count, 1)

    async def test_api_error_envelope_trips_api_circuit_without_raising(self) -> None:
        transport_breaker = CircuitBreaker(
            1, 30, max_cycles=0, name="transport"
        )
        api_breaker = CircuitBreaker(1, 30, max_cycles=0, name="api")
        response = SimpleNamespace(payload={"error": "rate limited"})

        class Target:
            _transport_circuit_breaker = transport_breaker
            _api_circuit_breaker = api_breaker
            _send_with_retries = AsyncMock(return_value=response)

        self.assertIs(await TransportMixin.send(Target(), object()), response)
        self.assertEqual(transport_breaker.state, CircuitBreakerState.CLOSED)
        self.assertEqual(api_breaker.state, CircuitBreakerState.OPEN)

    async def test_transport_cycle_retries_request_after_inner_retries_fail(
        self,
    ) -> None:
        breaker = CircuitBreaker(
            1,
            0,
            max_cycles=2,
            max_recovery_timeout=0,
            wait_when_open=False,
            name="transport",
        )
        response = SimpleNamespace(payload={})

        class Target:
            _transport_circuit_breaker = breaker
            _api_circuit_breaker = None
            _send_with_retries = AsyncMock(
                side_effect=[MapperTransportError("offline"), response]
            )

        target = Target()
        self.assertIs(await TransportMixin.send(target, object()), response)
        self.assertEqual(target._send_with_retries.await_count, 2)
        self.assertEqual(breaker.state, CircuitBreakerState.CLOSED)

    async def test_wait_when_open_false_restores_fail_fast_behavior(self) -> None:
        breaker = CircuitBreaker(
            1,
            30,
            max_cycles=0,
            wait_when_open=False,
            name="transport",
        )

        class Target:
            _transport_circuit_breaker = breaker
            _api_circuit_breaker = None
            _send_with_retries = AsyncMock(
                side_effect=MapperTransportError("offline")
            )

        target = Target()
        with self.assertRaises(MapperTransportError):
            await TransportMixin.send(target, object())
        with self.assertRaises(CircuitBreakerOpenError) as raised:
            await TransportMixin.send(target, object())

        self.assertEqual(raised.exception.circuit, "transport")
        self.assertEqual(target._send_with_retries.await_count, 1)

    async def test_transport_cycles_stop_at_configured_limit(self) -> None:
        breaker = CircuitBreaker(
            1,
            0,
            max_cycles=2,
            max_recovery_timeout=0,
            name="transport",
        )

        class Target:
            _transport_circuit_breaker = breaker
            _api_circuit_breaker = None
            _send_with_retries = AsyncMock(
                side_effect=MapperTransportError("offline")
            )

        target = Target()
        with self.assertRaises(MapperTransportError):
            await TransportMixin.send(target, object())
        self.assertEqual(target._send_with_retries.await_count, 3)
        self.assertEqual(breaker.state, CircuitBreakerState.OPEN)

    async def test_api_error_envelope_is_retried_until_success(self) -> None:
        breaker = CircuitBreaker(
            1,
            0,
            max_cycles=2,
            max_recovery_timeout=0,
            name="api",
        )
        error_response = SimpleNamespace(payload={"error": "rate limited"})
        success_response = SimpleNamespace(payload={})

        class Target:
            _transport_circuit_breaker = None
            _api_circuit_breaker = breaker
            _send_with_retries = AsyncMock(
                side_effect=[error_response, error_response, success_response]
            )

        target = Target()
        self.assertIs(
            await TransportMixin.send(target, object()),
            success_response,
        )
        self.assertEqual(target._send_with_retries.await_count, 3)
        self.assertEqual(breaker.state, CircuitBreakerState.CLOSED)

    async def test_cancelled_probe_is_released(self) -> None:
        clock = Clock()
        breaker = CircuitBreaker(1, 0, time_func=clock)
        permit = await breaker.before_call()
        await breaker.record_failure(permit)

        class Target:
            _transport_circuit_breaker = breaker
            _api_circuit_breaker = None
            _send_with_retries = AsyncMock(side_effect=asyncio.CancelledError)

        with self.assertRaises(asyncio.CancelledError):
            await TransportMixin.send(Target(), object())
        self.assertEqual(breaker.state, CircuitBreakerState.OPEN)
        await breaker.before_call()
        self.assertEqual(breaker.state, CircuitBreakerState.HALF_OPEN)

    async def test_lifecycle_preserves_circuit_error_from_task_group(self) -> None:
        manager = LifecycleManager(SimpleNamespace())  # type: ignore[arg-type]
        error = CircuitBreakerOpenError(1, circuit="transport")

        async def observe() -> None:
            await asyncio.Event().wait()

        async def connect() -> None:
            raise error

        with self.assertRaises(CircuitBreakerOpenError) as raised:
            await manager._observe_task(observe, connect)

        self.assertIs(raised.exception, error)

    async def test_lifecycle_waits_for_circuit_and_retries_authorization(self) -> None:
        breaker = SimpleNamespace(wait_until_available=AsyncMock())
        mapper = SimpleNamespace(
            transport_circuit_breaker=breaker,
            api_circuit_breaker=None,
        )
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        error = CircuitBreakerOpenError(1, circuit="transport")
        manager._authorize = AsyncMock(  # type: ignore[method-assign]
            side_effect=[error, None]
        )
        manager._handle_disconnect = AsyncMock()  # type: ignore[method-assign]
        backoff = Mock()

        await manager._authorize_cycle(None, backoff)

        self.assertEqual(manager._authorize.await_count, 2)
        breaker.wait_until_available.assert_awaited_once_with()
        manager._handle_disconnect.assert_not_awaited()
        backoff.reset.assert_called_once_with()

    async def test_keepalive_survives_fail_fast_circuit_error(self) -> None:
        error = CircuitBreakerOpenError(1, circuit="transport")

        class Target:
            _keepalive_ping_interval = 0
            keep_alive_interactive = True
            _logger = logging.getLogger("CircuitBreakerKeepaliveTest")
            send = AsyncMock(side_effect=[error, asyncio.CancelledError])

        with self.assertRaises(asyncio.CancelledError):
            await AuthMixin._keepalive(Target())  # type: ignore[arg-type]

        self.assertEqual(Target.send.await_count, 2)

    def test_config_defaults_and_validation(self) -> None:
        config = EnvelopeMapperConfigV11()
        self.assertEqual(
            config.circuit_breakers,
            MappingCircuitBreakersConfig(
                transport=CircuitBreakerConfig(),
                api=CircuitBreakerConfig(),
            ),
        )
        self.assertEqual(config.circuit_breakers.transport.max_cycles, 5)
        self.assertEqual(config.circuit_breakers.api.max_cycles, 5)
        self.assertTrue(config.circuit_breakers.transport.wait_when_open)
        self.assertTrue(config.circuit_breakers.api.wait_when_open)

        with self.assertRaises(ValueError):
            CircuitBreakerConfig(failure_threshold=0)
        with self.assertRaises(ValueError):
            CircuitBreakerConfig(max_cycles=-1)
        with self.assertRaises(ValueError):
            CircuitBreakerConfig(
                recovery_timeout=10,
                max_recovery_timeout=5,
            )
