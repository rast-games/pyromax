import unittest
from collections.abc import Callable
from typing import Any

from pyromax import MaxApi, RawUpdateMode, UpdateTranslationFailure
from pyromax.dispatcher import Dispatcher
from pyromax.dispatcher.event import ResolvedUpdate, Update
from pyromax.dispatcher.middlewares.event_resolvers import EventContext
from pyromax.dispatcher.middlewares.user_context import EVENT_CONTEXT_KEY
from pyromax.models import Message
from pyromax.protocol import ErrorResponse, Response


class RawResponse(Response):
    pass


class PollingApi:
    def __init__(
        self,
        updates: list[Response],
        translator: Callable[[Response], Any],
    ) -> None:
        self._updates = updates
        self._translator = translator
        self.shutdown_requested = False
        self.workflow_data: dict[Any, Any] = {}
        self.stopped = False

    def _add_disconnect_listener(self, listener: Any) -> None:
        self.disconnect_listener = listener

    def _remove_disconnect_listener(self, listener: Any) -> None:
        if self.disconnect_listener == listener:
            self.disconnect_listener = None

    def _add_unsupported_version_listener(self, listener: Any) -> None:
        self.version_listener = listener

    def _remove_unsupported_version_listener(self, listener: Any) -> None:
        if self.version_listener == listener:
            self.version_listener = None

    def listen_updates(self, context: dict[str, Any]) -> tuple[Any, Any]:
        async def updates():
            for update in self._updates:
                yield update

        return self._translator, updates()

    async def wait_until_ready(self) -> bool:
        return True

    async def stop(self) -> None:
        self.stopped = True


class RawUpdateModeTest(unittest.IsolatedAsyncioTestCase):
    async def test_translated_only_remains_the_default(self) -> None:
        update = RawResponse()
        seen: list[Response] = []
        dispatcher = Dispatcher(disable_fsm=True)

        @dispatcher.update.outer_middleware()
        async def raw_middleware(handler, event, data):
            seen.append(event)
            return await handler(event, data)

        def fail_translation(_update: Response) -> Any:
            raise ValueError("invalid update")

        api = PollingApi([update], fail_translation)
        await dispatcher.start_polling(api)  # type: ignore[arg-type]

        self.assertEqual(seen, [])
        self.assertTrue(api.stopped)

    async def test_all_responses_dispatches_translation_failures_as_raw(self) -> None:
        update = RawResponse()
        failure = ValueError("invalid update")
        seen: list[tuple[Response, dict[Any, Any]]] = []
        dispatcher = Dispatcher(
            raw_update_mode=RawUpdateMode.ALL_RESPONSES,
        )

        @dispatcher.update.outer_middleware()
        async def raw_middleware(handler, event, data):
            seen.append((event, data.copy()))
            return await handler(event, data)

        def fail_translation(_update: Response) -> Any:
            raise failure

        api = PollingApi([update], fail_translation)
        api.workflow_data[MaxApi] = api
        await dispatcher.start_polling(api)  # type: ignore[arg-type]

        self.assertEqual(len(seen), 1)
        event, data = seen[0]
        self.assertIs(event, update)
        self.assertIs(data[Update], update)
        self.assertIs(data[ResolvedUpdate], update)
        self.assertIs(data[UpdateTranslationFailure].exception, failure)
        self.assertEqual(data[EVENT_CONTEXT_KEY], EventContext())

    async def test_all_responses_also_dispatches_error_responses(self) -> None:
        update = ErrorResponse(RuntimeError("receive failed"))
        seen: list[tuple[Response, dict[Any, Any]]] = []
        dispatcher = Dispatcher(
            disable_fsm=True,
            raw_update_mode="all_responses",  # type: ignore[arg-type]
        )

        @dispatcher.update.outer_middleware()
        async def raw_middleware(handler, event, data):
            seen.append((event, data.copy()))
            return await handler(event, data)

        def translator_must_not_run(_update: Response) -> Any:
            raise AssertionError("ErrorResponse must not be translated")

        await dispatcher.start_polling(  # type: ignore[arg-type]
            PollingApi([update], translator_must_not_run)
        )

        self.assertEqual(len(seen), 1)
        event, data = seen[0]
        self.assertIs(event, update)
        self.assertIs(data[Update], update)
        self.assertIs(data[ResolvedUpdate], update)
        self.assertNotIn(UpdateTranslationFailure, data)

    async def test_all_responses_keeps_typed_dispatch_after_translation(self) -> None:
        update = RawResponse()
        resolved = Message(
            message_id=1,
            chat_id=2,
            time=3,
            type="USER",
            text="hello",
            cid=None,
        )
        raw_data: list[dict[Any, Any]] = []
        typed_events: list[Message] = []
        dispatcher = Dispatcher(
            disable_fsm=True,
            raw_update_mode=RawUpdateMode.ALL_RESPONSES,
        )

        @dispatcher.update.outer_middleware()
        async def raw_middleware(handler, event, data):
            raw_data.append(data.copy())
            return await handler(event, data)

        @dispatcher.message(from_me=True)
        async def message_handler(event: Message) -> None:
            typed_events.append(event)

        await dispatcher.start_polling(  # type: ignore[arg-type]
            PollingApi([update], lambda _update: resolved)
        )

        self.assertEqual(typed_events, [resolved])
        self.assertIs(raw_data[0][Update], update)
        self.assertIs(raw_data[0][ResolvedUpdate], resolved)
        self.assertNotIn(UpdateTranslationFailure, raw_data[0])

    def test_unknown_mode_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Dispatcher(raw_update_mode="unknown")  # type: ignore[arg-type]
