import asyncio
import unittest

from pyromax.exceptions import AlreadyCancelledError, RequestWasCancelledError
from pyromax.protocol.envelope.envelope import Envelope
from pyromax.routing.event_router import EventRouter


class EventRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_matching_response_resolves_only_its_request(self) -> None:
        router = EventRouter[Envelope, Envelope]()
        request = Envelope(seq=1, cmd=0, opcode=10, payload={})
        future = router.create_record(request, gen=2)
        response = Envelope(seq=1, cmd=1, opcode=10, payload={"ok": True})

        self.assertFalse(await router.resolve_response(response, gen=1))
        self.assertFalse(future.done())
        self.assertEqual(await router.pop_all_updates(), [response])

        self.assertTrue(await router.resolve_response(response, gen=2))
        self.assertIs(await future, response)

    async def test_unmatched_responses_are_batched_as_updates(self) -> None:
        router = EventRouter[Envelope, Envelope]()
        first = Envelope(seq=1, cmd=1, opcode=1, payload={})
        second = Envelope(seq=2, cmd=1, opcode=2, payload={})
        await router.add_to_updates(first)
        await router.add_to_updates(second)
        self.assertEqual(await router.pop_all_updates(), [first, second])

    async def test_cancel_request_removes_pending_record(self) -> None:
        router = EventRouter[Envelope, Envelope]()
        request = Envelope(seq=1, cmd=0, opcode=1, payload={})
        future = router.create_record(request, 1)
        router.cancel_request(request, 1)
        self.assertFalse(await router.resolve_response(
            Envelope(seq=1, cmd=1, opcode=1, payload={}), 1
        ))
        self.assertFalse(future.done())
        future.cancel()

    async def test_cancel_all_fails_waiters_and_prevents_new_records(self) -> None:
        router = EventRouter[Envelope, Envelope]()
        request = Envelope(seq=1, cmd=0, opcode=1, payload={})
        future = router.create_record(request, 1)
        update_waiter = asyncio.create_task(router.pop_all_updates())
        await asyncio.sleep(0)

        await router.cancel_all()

        with self.assertRaises(RequestWasCancelledError):
            await future
        with self.assertRaises(AlreadyCancelledError):
            await update_waiter
        with self.assertRaises(AlreadyCancelledError):
            router.create_record(request, 2)
