import unittest
from collections.abc import Awaitable, Callable
from typing import Any

from pyromax import F
from pyromax.dispatcher.Dispatcher import Dispatcher
from pyromax.dispatcher.Router import Router
from pyromax.exceptions import UnsupportedClientVersionMapperError
from pyromax.models import (
    DataDict,
    DisconnectEvent,
    ErrorEvent,
    UnsupportedClientVersionEvent,
)


class RouterStructureTest(unittest.TestCase):
    def test_include_builds_head_and_tail_chains(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        grandchild = Router(name="grandchild")
        root.include_router(child)
        child.include_router(grandchild)

        self.assertEqual(list(root.chain_tail), [root, child, grandchild])
        self.assertEqual(list(grandchild.chain_head), [grandchild, child, root])

    def test_invalid_self_duplicate_and_circular_links_are_rejected(self) -> None:
        root = Router(name="root")
        child = Router(name="child")
        with self.assertRaises(ValueError):
            root.include_router(object())  # type: ignore[arg-type]
        with self.assertRaises(RuntimeError):
            root.include_router(root)
        root.include_router(child)
        with self.assertRaises(RuntimeError):
            Router(name="other").include_router(child)
        with self.assertRaises(RuntimeError):
            child.include_router(root)

    def test_include_routers_requires_at_least_one_child(self) -> None:
        with self.assertRaisesRegex(ValueError, "At least one"):
            Router().include_routers()


class DisconnectHandlerTest(unittest.IsolatedAsyncioTestCase):
    async def test_unsupported_version_uses_dispatcher_and_di(self) -> None:
        dispatcher = Dispatcher(disable_fsm=True)
        selected: list[str] = []

        class DispatchApi:
            workflow_data: dict[Any, Any] = {}

            async def set_app_version(
                self,
                app_version: str,
                *,
                reconnect: bool = True,
            ) -> str:
                selected.append(app_version)
                self.reconnect = reconnect
                return app_version

        api = DispatchApi()

        @dispatcher.unsupported_version()
        async def handler(
            event: UnsupportedClientVersionEvent,
            injected_api: DispatchApi,
        ) -> None:
            self.assertIs(injected_api, api)
            self.assertEqual(event.app_version, "26.25.0")
            await injected_api.set_app_version("26.35.1", reconnect=False)

        error = UnsupportedClientVersionMapperError(
            "unsupported",
            app_version="26.25.0",
        )
        event = UnsupportedClientVersionEvent(
            exception=error,
            app_version="26.25.0",
            available_versions=("26.25.0", "26.35.1"),
        )

        await dispatcher._process_unsupported_client_version(  # type: ignore[arg-type]
            event,
            api,
        )

        self.assertEqual(selected, ["26.35.1"])
        self.assertFalse(api.reconnect)

    async def test_disconnect_uses_nested_router_filter_middleware_and_di(self) -> None:
        dispatcher = Dispatcher(disable_fsm=True)
        child = Router(name="child")
        dispatcher.include_router(child)

        class Marker:
            pass

        marker = Marker()
        seen: list[str] = []

        @dispatcher.disconnect.middleware()
        async def disconnect_middleware(
            handler: Callable[[DisconnectEvent, dict[Any, Any]], Awaitable[Any]],
            event: DisconnectEvent,
            data: dict[Any, Any],
        ) -> Any:
            seen.append("middleware")
            return await handler(event, data)

        @child.disconnect(F.reconnect)
        async def child_handler(
            event: DisconnectEvent,
            injected_marker: Marker,
            data: DataDict,
        ) -> None:
            self.assertIs(injected_marker, marker)
            self.assertIs(data[DisconnectEvent], event)
            self.assertIs(event.bot, api)
            seen.append(str(event.exception))

        class DispatchApi:
            workflow_data = {Marker: marker}

        api = DispatchApi()
        event = DisconnectEvent(
            exception=ConnectionError("lost"),
            reconnect=True,
            delay=1.5,
        )

        await dispatcher._process_disconnect(event, api)  # type: ignore[arg-type]

        self.assertEqual(seen, ["middleware", "lost"])

        await dispatcher._process_disconnect(  # type: ignore[arg-type]
            DisconnectEvent(
                exception=ConnectionError("ignored"),
                reconnect=False,
                delay=0.0,
            ),
            api,
        )
        self.assertEqual(seen, ["middleware", "lost"])

    async def test_disconnect_handler_error_uses_error_observer(self) -> None:
        dispatcher = Dispatcher(disable_fsm=True)
        errors: list[ErrorEvent] = []

        @dispatcher.disconnect()
        async def broken_handler(
            _event: DisconnectEvent,
        ) -> None:
            raise RuntimeError("handler failed")

        @dispatcher.error()
        async def error_handler(
            event: ErrorEvent,
        ) -> None:
            errors.append(event)

        class DispatchApi:
            workflow_data: dict[Any, Any] = {}

        disconnect = DisconnectEvent(
            exception=ConnectionError("lost"),
            reconnect=True,
            delay=0.0,
        )
        await dispatcher._process_disconnect(  # type: ignore[arg-type]
            disconnect,
            DispatchApi(),
        )

        self.assertEqual(len(errors), 1)
        self.assertIs(errors[0].update, disconnect)
        self.assertEqual(str(errors[0].exception), "handler failed")

    async def test_polling_binds_and_unbinds_disconnect_notifications(self) -> None:
        dispatcher = Dispatcher(disable_fsm=True)
        seen: list[tuple[str, bool, float]] = []

        @dispatcher.disconnect()
        async def handler(
            event: DisconnectEvent,
        ) -> None:
            seen.append((str(event.exception), event.reconnect, event.delay))

        class PollingApi:
            def __init__(self) -> None:
                self.listener = None
                self.workflow_data = {}
                self.stopped = False

            def _add_disconnect_listener(self, listener) -> None:
                self.listener = listener

            def _remove_disconnect_listener(self, listener) -> None:
                if self.listener == listener:
                    self.listener = None

            def _add_unsupported_version_listener(self, listener) -> None:
                self.version_listener = listener

            def _remove_unsupported_version_listener(self, listener) -> None:
                if self.version_listener == listener:
                    self.version_listener = None

            def listen_updates(self, context):
                async def updates():
                    assert self.listener is not None
                    await self.listener(
                        DisconnectEvent(
                            exception=ConnectionError("offline"),
                            reconnect=True,
                            delay=0.0,
                        ),
                        self,
                    )
                    if False:
                        yield None

                return lambda update: update, updates()

            async def stop(self) -> None:
                self.stopped = True

        api = PollingApi()
        await dispatcher.start_polling(api)  # type: ignore[arg-type]

        self.assertEqual(seen, [("offline", True, 0.0)])
        self.assertIsNone(api.listener)
        self.assertTrue(api.stopped)
