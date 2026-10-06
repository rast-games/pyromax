import unittest

from pyromax.dispatcher.Router import Router
from pyromax.dispatcher.event.Handler import FilterObject, Handler
from pyromax.dispatcher.event.UpdateType import UNKNOWN_UPDATE
from pyromax.filters.base import Filter
from pyromax.filters.logic import and_f, invert_f, or_f
from pyromax.models.Chat import Chat
from pyromax.models.Message import Message


def message() -> Message:
    return Message(message_id=1, chat_id=2, time=3, type="USER", text="hello", cid=None)


class StaticMessageFilter(Filter):
    def __init__(self, result):
        super().__init__()
        self.result = result
        self.calls = 0

    @property
    def work_with(self):
        return (Message,)

    async def _check(self, message: Message):
        self.calls += 1
        return self.result


class DispatcherAndFilterTest(unittest.IsolatedAsyncioTestCase):
    async def test_filter_rejects_wrong_update_type_without_calling_check(self) -> None:
        filter_ = StaticMessageFilter(True)
        chat = Chat(id=1, type="CHAT", status="ACTIVE", owner=1)
        self.assertFalse(await filter_(chat, {}))  # type: ignore[arg-type]
        self.assertEqual(filter_.calls, 0)

    async def test_logic_filters_short_circuit_and_merge_context(self) -> None:
        first = StaticMessageFilter({"first": 1})
        second = StaticMessageFilter({"second": 2})
        false = StaticMessageFilter(False)
        update = message()

        data = {Message: update}
        self.assertEqual(await and_f(first, second)._check(update, data), {"first": 1, "second": 2})
        self.assertFalse(await and_f(false, second)._check(update, data))
        self.assertEqual(second.calls, 1)
        self.assertEqual(await or_f(false, first)._check(update, data), {"first": 1})
        self.assertTrue(await invert_f(false)._check(update, data))

    async def test_handler_filter_context_isolated_from_input(self) -> None:
        filter_ = StaticMessageFilter({"captured": "value"})

        async def callback(event: Message) -> Message:
            return event

        handler = Handler(callback, [FilterObject(filter_)])
        original = {"untouched": True, Message: message()}
        accepted, enriched = await handler.check(message(), original)
        self.assertTrue(accepted)
        self.assertEqual(enriched["captured"], "value")
        self.assertEqual(original["untouched"], True)
        self.assertNotIn("captured", original)
        self.assertIs(await handler.update(message(), enriched), original[Message])

    async def test_router_dispatches_typed_message_and_returns_handler_result(self) -> None:
        router = Router(name="root")
        seen: list[Message] = []

        @router.message(from_me=True)
        async def handle(event: Message) -> str:
            seen.append(event)
            return "handled"

        update = message()
        result = await router.notify(update, {Message: update})
        self.assertEqual(result, "handled")
        self.assertEqual(seen, [update])

    async def test_router_requires_data_and_marks_unknown_types(self) -> None:
        router = Router()
        update = message()
        with self.assertRaisesRegex(ValueError, "data cannot be None"):
            await router.notify(update)
        self.assertIs(
            await router.notify(object(), {}),  # type: ignore[arg-type]
            UNKNOWN_UPDATE,
        )
