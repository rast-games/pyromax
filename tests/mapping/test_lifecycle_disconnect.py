import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from pyromax.mapping.envelope.v11.LifecycleManager import (
    LifecycleFailure,
    LifecycleManager,
)
from pyromax.models import DisconnectEvent


class LifecycleDisconnectTest(unittest.IsolatedAsyncioTestCase):
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

        manager = LifecycleManager(Mapper())  # type: ignore[arg-type]
        error = ConnectionError("lost")
        manager._lifecycle_queue.put_nowait(LifecycleFailure(error, "test", 0))

        async def authorize_cycle(*args, **kwargs) -> None:
            nonlocal authorize_calls
            authorize_calls += 1
            if authorize_calls == 2:
                raise asyncio.CancelledError

        manager._authorize_cycle = authorize_cycle  # type: ignore[method-assign]

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

        manager = LifecycleManager(Mapper())  # type: ignore[arg-type]
        error = ConnectionError("lost")
        manager._lifecycle_queue.put_nowait(LifecycleFailure(error, "test", 0))

        authorize_cycle = AsyncMock()
        manager._authorize_cycle = authorize_cycle  # type: ignore[method-assign]

        await manager._manage_lifecycle()

        self.assertEqual(len(emitted), 1)
        self.assertIs(emitted[0].exception, error)
        self.assertFalse(emitted[0].reconnect)
        self.assertEqual(emitted[0].delay, 3.0)
        self.assertTrue(Mapper.max_api.shutdown_requested)
        authorize_cycle.assert_awaited_once()
