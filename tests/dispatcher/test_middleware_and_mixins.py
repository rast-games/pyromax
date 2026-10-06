import unittest

from pyromax.dispatcher.middlewares.manager import MiddlewareManager
from pyromax.mixins.AsyncInitializer import AsyncInitializerMixin
from pyromax.mixins.SingletonMeta import SingletonMeta


class MiddlewareManagerTest(unittest.IsolatedAsyncioTestCase):
    async def test_registration_order_wrapping_and_unregister(self) -> None:
        manager = MiddlewareManager()
        trace: list[str] = []

        async def first(handler, event, data):
            trace.append("first-before")
            result = await handler(event, data)
            trace.append("first-after")
            return result

        @manager()
        async def second(handler, event, data):
            trace.append("second-before")
            result = await handler(event, data)
            trace.append("second-after")
            return result

        manager.register(first)

        async def handler(event, data):
            trace.append("handler")
            return event + data["increment"]

        wrapped = manager.wrap_middlewares(manager, handler)
        self.assertEqual(await wrapped(2, {"increment": 3}), 5)
        self.assertEqual(trace, [
            "second-before", "first-before", "handler", "first-after", "second-after"
        ])
        self.assertEqual(len(manager), 2)
        self.assertIs(manager[0], second)
        manager.unregister(first)
        self.assertEqual(list(manager), [second])


class MixinTest(unittest.IsolatedAsyncioTestCase):
    async def test_async_initializer_returns_initialized_instance(self) -> None:
        class Resource(AsyncInitializerMixin):
            async def _async_init(self, value: int) -> None:
                self.value = value

        resource = await Resource(7)
        self.assertIsInstance(resource, Resource)
        self.assertEqual(resource.value, 7)

    def test_singleton_is_scoped_per_class_and_keeps_first_init(self) -> None:
        class First(metaclass=SingletonMeta):
            def __init__(self, value: int) -> None:
                self.value = value

        class Second(metaclass=SingletonMeta):
            pass

        first = First(1)
        self.assertIs(First(2), first)
        self.assertEqual(first.value, 1)
        self.assertIsNot(first, Second())
