import asyncio
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from pyromax.mapping.envelope.v11.mixins.construct import ConstructorMixin
from pyromax.mapping.envelope.v11.mixins.message import MessageMixin


class MessageMixinTest(unittest.IsolatedAsyncioTestCase):
    async def test_send_message_propagates_task_cancellation(self) -> None:
        class Target:
            _next_cid = Mock(return_value=123)
            send = AsyncMock(side_effect=asyncio.CancelledError)

        with self.assertRaises(asyncio.CancelledError):
            await MessageMixin.send_message(Target(), chat_id=1, text="hello")

        Target.send.assert_awaited_once()

    def test_next_cid_is_monotonic_when_clock_does_not_move(self) -> None:
        target = SimpleNamespace(
            _previous_cid=0,
            _cid_lock=threading.Lock(),
        )

        with patch(
            "pyromax.mapping.envelope.v11.mixins.construct.time.time",
            return_value=1_700_000_000.123,
        ):
            cids = [
                ConstructorMixin._next_cid(target)  # type: ignore[arg-type]
                for _ in range(100)
            ]

        self.assertEqual(cids, list(range(cids[0], cids[0] + 100)))

    async def test_send_message_uses_generated_negative_cid(self) -> None:
        class Target:
            _next_cid = Mock(return_value=123)
            send = AsyncMock(side_effect=asyncio.CancelledError)

        with self.assertRaises(asyncio.CancelledError):
            await MessageMixin.send_message(Target(), chat_id=1, text="hello")

        method = Target.send.await_args.kwargs["method"]
        self.assertEqual(method.args["cid"], -123)
        Target._next_cid.assert_called_once_with()
