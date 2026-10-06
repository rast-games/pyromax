import asyncio
import unittest

from pyromax.exceptions import DataNotDictLikeError
from pyromax.fsm.context import FSMContext
from pyromax.fsm.state import RawState, State, StatesGroup, any_state
from pyromax.fsm.storage.base import DefaultKeyBuilder, StorageKey
from pyromax.fsm.storage.memory import MemoryStorage, SimpleEventIsolation


class Form(StatesGroup):
    name = State()

    class Address(StatesGroup):
        city = State()


class FSMTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.key = StorageKey(max_api_id=1, chat_id=2, user_id=3)

    def test_state_group_names_membership_and_matching(self) -> None:
        self.assertEqual(Form.name.state, "Form:name")
        self.assertEqual(Form.Address.city.state, "Form.Address:city")
        self.assertIn(Form.name, Form)
        self.assertIn("Form.Address:city", Form)
        self.assertIn(Form.Address, Form)
        self.assertEqual(Form.Address.get_root(), Form)
        self.assertTrue(Form.name(None, {RawState: "Form:name"}))  # type: ignore[arg-type]
        self.assertTrue(any_state(None, {}))  # type: ignore[arg-type]

    def test_ungrouped_state_has_no_group(self) -> None:
        state = State("loose")
        self.assertEqual(state.state, "@:loose")
        with self.assertRaises(RuntimeError):
            _ = state.group

    def test_key_builder_variants_and_destiny_guard(self) -> None:
        self.assertEqual(DefaultKeyBuilder().build(self.key, "state"), "fsm:2:3:state")
        builder = DefaultKeyBuilder(prefix="p", separator="/", with_bot_id=True, with_destiny=True)
        self.assertEqual(builder.build(self.key, "data"), "p/1/2/3/default/data")
        custom = StorageKey(1, 2, 3, destiny="custom")
        with self.assertRaisesRegex(ValueError, "with_destiny=True"):
            DefaultKeyBuilder().build(custom)

    async def test_memory_storage_and_context_lifecycle(self) -> None:
        storage = MemoryStorage()
        context = FSMContext(storage, self.key)
        await context.set_state(Form.name)
        await context.set_data({"count": 1, "nested": []})
        self.assertEqual(await context.get_state(), "Form:name")
        self.assertEqual(await context.get_value("count"), 1)
        self.assertEqual(await context.update_data({"count": 2}, extra=True), {"count": 2, "nested": [], "extra": True})
        await context.clear()
        self.assertIsNone(await context.get_state())
        self.assertEqual(await context.get_data(), {})

    async def test_memory_storage_copies_top_level_data(self) -> None:
        storage = MemoryStorage()
        original = {"value": 1}
        await storage.set_data(self.key, original)
        original["value"] = 2
        received = await storage.get_data(self.key)
        received["value"] = 3
        self.assertEqual(await storage.get_data(self.key), {"value": 1})
        with self.assertRaises(DataNotDictLikeError):
            await storage.set_data(self.key, [("x", 1)])  # type: ignore[arg-type]

    async def test_simple_isolation_serializes_same_key(self) -> None:
        isolation = SimpleEventIsolation()
        order: list[str] = []

        async def worker(name: str) -> None:
            async with isolation.lock(self.key):
                order.append(name + "-start")
                await asyncio.sleep(0)
                order.append(name + "-end")

        await asyncio.gather(worker("a"), worker("b"))
        self.assertEqual(order, ["a-start", "a-end", "b-start", "b-end"])
        await isolation.close()
