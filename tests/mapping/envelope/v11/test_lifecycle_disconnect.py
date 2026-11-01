import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pyromax.exceptions import MapperConnectError
from pyromax.mapping.envelope.v11.LifecycleManager import (
    LifecycleFailure,
    LifecycleManager,
    _LifecycleStates,
)
from pyromax.models import DisconnectEvent


class LifecycleDisconnectTest(unittest.IsolatedAsyncioTestCase):
    async def test_connect_timeout_is_applied(self) -> None:
        class Mapper:
            async def close(self, _exception=None) -> None:
                return None

            async def connect(self) -> None:
                await asyncio.Event().wait()

        manager = LifecycleManager(
            Mapper(),  # type: ignore[arg-type]
            connect_timeout=0.01,  # type: ignore[arg-type]
        )

        with self.assertRaises(MapperConnectError):
            await manager._connect()

        self.assertEqual(manager.get_generation(), 1)
        self.assertIs(manager._state, _LifecycleStates.DISCONNECTED)

    async def test_authorize_starts_telemetry_after_authentication(self) -> None:
        telemetry = SimpleNamespace(start=AsyncMock())
        send_user_agent = AsyncMock()

        class Mapper:
            logged = True
            _telemetry = telemetry

            async def close(self, _exception=None) -> None:
                return None

            async def connect(self) -> None:
                return None

            async def _send_user_agent(self) -> None:
                await send_user_agent()

            async def _send_auth_token(self) -> None:
                return None

        mapper = Mapper()
        mapper._mapper_connected = asyncio.Event()
        mapper._mapper_connected.set()
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]

        await manager._authorize()

        send_user_agent.assert_awaited_once_with()
        telemetry.start.assert_awaited_once_with()

    async def test_reconnect_closes_send_gates_before_queueing_failure(self) -> None:
        mapper = SimpleNamespace(
            _authorized=asyncio.Event(),
            _mapper_connected=asyncio.Event(),
            _protocol_connected=asyncio.Event(),
        )
        mapper._authorized.set()
        mapper._mapper_connected.set()
        mapper._protocol_connected.set()
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        manager._state = _LifecycleStates.CONNECTED
        manager._running = True
        manager.wait_until_connected = AsyncMock()  # type: ignore[method-assign]
        error = ConnectionError("reconnect requested")

        await manager.request_reconnect(error)

        self.assertFalse(mapper._authorized.is_set())
        self.assertFalse(mapper._mapper_connected.is_set())
        self.assertFalse(mapper._protocol_connected.is_set())
        failure = manager._lifecycle_queue.get_nowait()
        self.assertIs(failure.exception, error)
        manager.wait_until_connected.assert_awaited_once_with()

    async def test_connection_failure_is_emitted_before_reconnect(self) -> None:
        emitted: list[DisconnectEvent] = []
        authorize_calls = 0

        class Api:
            async def _emit_disconnect(
                self,
                event: DisconnectEvent,
            ) -> None:
                emitted.append(event)

        class Mapper:
            max_api = Api()
            extra_config = SimpleNamespace(reconnect=True, reconnect_delay=1.5)

            async def close(self, _exception=None) -> None:
                return None

            async def _handle_disconnect(self, exception: Exception) -> bool:
                await self.max_api._emit_disconnect(
                    DisconnectEvent(
                        exception=exception,
                        reconnect=True,
                        delay=1.5,
                    )
                )
                await asyncio.sleep(1.5)
                return True

        mapper = Mapper()
        mapper._mapper_connected = asyncio.Event()
        mapper._mapper_connected.set()
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        manager._state = _LifecycleStates.CONNECTED
        manager._running = True
        error = ConnectionError("lost")
        manager._lifecycle_queue.put_nowait(LifecycleFailure(error, "test", 0))

        async def authorize() -> None:
            nonlocal authorize_calls
            authorize_calls += 1
            raise asyncio.CancelledError

        manager._authorize = authorize  # type: ignore[method-assign]

        sleep = AsyncMock()
        with (
            patch(
                "pyromax.mapping.envelope.v11.LifecycleManager.asyncio.sleep",
                sleep,
            ),
            self.assertRaises(asyncio.CancelledError),
        ):
            await manager._manage_lifecycle()

        self.assertEqual(len(emitted), 1)
        self.assertIs(emitted[0].exception, error)
        self.assertTrue(emitted[0].reconnect)
        self.assertEqual(emitted[0].delay, 1.5)
        sleep.assert_awaited_once_with(1.5)
        self.assertEqual(authorize_calls, 1)

    async def test_disabled_reconnect_emits_and_requests_shutdown(self) -> None:
        emitted: list[DisconnectEvent] = []

        class Api:
            def __init__(self) -> None:
                self.shutdown_requested = False

            async def _emit_disconnect(
                self,
                event: DisconnectEvent,
            ) -> None:
                emitted.append(event)

            def request_shutdown(self) -> None:
                self.shutdown_requested = True

        class Mapper:
            max_api = Api()
            extra_config = SimpleNamespace(reconnect=False, reconnect_delay=3.0)

            async def close(self, _exception=None) -> None:
                return None

            async def _handle_disconnect(self, exception: Exception) -> bool:
                await self.max_api._emit_disconnect(
                    DisconnectEvent(
                        exception=exception,
                        reconnect=False,
                        delay=3.0,
                    )
                )
                return False

        mapper = Mapper()
        mapper._mapper_connected = asyncio.Event()
        mapper._mapper_connected.set()
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        manager._state = _LifecycleStates.CONNECTED
        manager._running = True
        error = ConnectionError("lost")
        manager._lifecycle_queue.put_nowait(LifecycleFailure(error, "test", 0))

        with self.assertRaises(ConnectionError) as raised:
            await manager._manage_lifecycle()

        self.assertIs(raised.exception, error)
        self.assertEqual(len(emitted), 1)
        self.assertIs(emitted[0].exception, error)
        self.assertFalse(emitted[0].reconnect)
        self.assertEqual(emitted[0].delay, 3.0)
        self.assertTrue(Mapper.max_api.shutdown_requested)
