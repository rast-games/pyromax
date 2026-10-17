import logging
import unittest
from unittest.mock import patch

from pyromax.core.client import MaxApi
from pyromax.dispatcher import Dispatcher
from pyromax.exceptions import UnsupportedClientVersionMapperError
from pyromax.models import DisconnectEvent, UnsupportedClientVersionEvent


class MaxApiDisconnectTest(unittest.IsolatedAsyncioTestCase):
    async def test_internal_disconnect_listeners_are_isolated(self) -> None:
        api = object.__new__(MaxApi)
        api._disconnect_listeners = []
        api._logger = logging.getLogger("MaxApiDisconnectTest")
        seen: list[DisconnectEvent] = []

        async def broken(_event: DisconnectEvent, _api: MaxApi) -> None:
            raise RuntimeError("broken listener")

        async def collect(event: DisconnectEvent, source_api: MaxApi) -> None:
            self.assertIs(source_api, api)
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

    async def test_dispatcher_listeners_can_be_loaded_by_multiple_apis(
        self,
    ) -> None:
        dispatcher = Dispatcher(disable_fsm=True)
        seen: list[MaxApi] = []

        @dispatcher.unsupported_version()
        async def handle_unsupported_version(
            _event: UnsupportedClientVersionEvent,
            api: MaxApi,
        ) -> None:
            seen.append(api)

        apis = (object.__new__(MaxApi), object.__new__(MaxApi))
        for api in apis:
            api._unsupported_version_listeners = []
            api._disconnect_listeners = []
            api._logger = logging.getLogger("MaxApiDispatcherListenersTest")
            api.workflow_data = {}
            api._load_dispatcher_lifecycle_listeners(dispatcher)
            api._load_dispatcher_lifecycle_listeners(dispatcher)

        error = UnsupportedClientVersionMapperError(
            "unsupported",
            app_version="26.25.0",
        )
        for api in apis:
            await api._emit_unsupported_version(
                UnsupportedClientVersionEvent(
                    exception=error,
                    app_version="26.25.0",
                    available_versions=("26.25.0", "26.35.1"),
                )
            )

        self.assertEqual(seen, list(apis))
        self.assertEqual(
            [len(api._unsupported_version_listeners) for api in apis],
            [1, 1],
        )
        self.assertTrue(all(not hasattr(api, "dispatcher") for api in apis))
