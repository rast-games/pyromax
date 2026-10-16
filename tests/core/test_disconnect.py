import logging
import unittest
from unittest.mock import patch

from pyromax.core.client import MaxApi
from pyromax.models import DisconnectEvent


class MaxApiDisconnectTest(unittest.IsolatedAsyncioTestCase):
    async def test_internal_disconnect_listeners_are_isolated(self) -> None:
        api = object.__new__(MaxApi)
        api._disconnect_listeners = []
        api._logger = logging.getLogger("MaxApiDisconnectTest")
        seen: list[DisconnectEvent] = []

        async def broken(_event: DisconnectEvent) -> None:
            raise RuntimeError("broken listener")

        async def collect(event: DisconnectEvent) -> None:
            seen.append(event)

        api._add_disconnect_listener(broken)
        api._add_disconnect_listener(collect)
        event = DisconnectEvent(
            exception=ConnectionError("lost"),
            reconnect=False,
            delay=2.0,
        )

        with patch.object(api._logger, "exception") as log_error:
            await api._emit_disconnect(event)

        self.assertEqual(seen, [event])
        log_error.assert_called_once()
