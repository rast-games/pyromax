import asyncio
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from pyromax.exceptions import (
    CloseProtocolError,
    CloseTransportError,
    ConnectProtocolError,
    ConnectTransportError,
    MapperCloseError,
)
from pyromax.mapping.envelope.v11.mixins.transport import TransportMixin
from pyromax.protocol.envelope import EnvelopeProtocol


class ConnectionCleanupTest(unittest.IsolatedAsyncioTestCase):
    async def test_close_failure_does_not_mask_connect_failure(self) -> None:
        connect_error = ConnectTransportError("connect failed")
        transport = SimpleNamespace(
            connect=AsyncMock(side_effect=connect_error),
            close=AsyncMock(
                side_effect=[None, CloseTransportError("cleanup failed")]
            ),
        )
        protocol = object.__new__(EnvelopeProtocol)
        protocol._network_lock = asyncio.Lock()
        protocol._transport = transport
        protocol._reader_task = None
        protocol.event_router = None
        protocol._logger = logging.getLogger("ConnectionCleanupTest")

        with self.assertRaises(ConnectProtocolError) as raised:
            await protocol.connect()

        self.assertIs(raised.exception.__cause__, connect_error)
        self.assertEqual(transport.close.await_count, 2)

    async def test_mapper_close_clears_protocol_gate_on_close_error(self) -> None:
        close_error = CloseProtocolError("close failed")
        target = SimpleNamespace(
            _telemetry=None,
            _keepalive_task=None,
            _mapper_connected=asyncio.Event(),
            _authorized=asyncio.Event(),
            _protocol_connected=asyncio.Event(),
            protocol=SimpleNamespace(close=AsyncMock(side_effect=close_error)),
            _logger=logging.getLogger("ConnectionCleanupTest"),
        )
        target._mapper_connected.set()
        target._authorized.set()
        target._protocol_connected.set()

        with self.assertRaises(MapperCloseError) as raised:
            await TransportMixin.close(target, close_error)  # type: ignore[arg-type]

        self.assertIs(raised.exception.__cause__, close_error)
        self.assertFalse(target._mapper_connected.is_set())
        self.assertFalse(target._authorized.is_set())
        self.assertFalse(target._protocol_connected.is_set())
        target.protocol.close.assert_awaited_once_with(close_error)
