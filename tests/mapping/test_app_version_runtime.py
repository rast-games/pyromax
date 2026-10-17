import asyncio
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from pyromax.config import (
    DesktopEnvelopeMappingUserAgentConfigV11,
    EnvelopeMapperConfigV11,
    ExtraConfig,
)
from pyromax.core.client import MaxApi
from pyromax.exceptions import (
    MapperApiError,
    MapperLifecycleError,
    MapperRestartCycleError,
    MapperTransportError,
    UnsupportedClientVersionMapperError,
)
from pyromax.mapping.envelope.v11.LifecycleManager import LifecycleManager
from pyromax.mapping.envelope.v11.constants import ErrorCode
from pyromax.mapping.envelope.v11.methods.build_ins.socket_methods import (
    SocketLoginBuildInMappingMethod,
)
from pyromax.mapping.envelope.v11.mixins.construct import ConstructorMixin
from pyromax.mapping.envelope.v11.mixins.transport import TransportMixin
from pyromax.mapping.envelope.v11.payloads.models import AppUserAgentMappingModel
from pyromax.models import DeviceType, SessionInfo, UnsupportedClientVersionEvent
from pyromax.protocol.envelope import Envelope
from pyromax.versions import VersionApi


class UnsupportedClientVersionTest(unittest.IsolatedAsyncioTestCase):
    async def test_sms_auth_does_not_retry_when_transport_is_closed(self) -> None:
        api_error = MapperApiError("temporary API error")
        api_error.error = "temporary.error"
        mapper = SimpleNamespace(
            phone="79990000000",
            protocol=SimpleNamespace(
                transport=SimpleNamespace(connected=False),
            ),
            request_code=AsyncMock(side_effect=api_error),
            log=Mock(),
        )

        with self.assertRaises(MapperTransportError) as raised:
            await SocketLoginBuildInMappingMethod()._resolve_sms_auth(
                mapper  # type: ignore[arg-type]
            )

        self.assertIs(raised.exception.__cause__, api_error)
        mapper.request_code.assert_awaited_once()

    async def test_sms_auth_does_not_retry_unsupported_version(self) -> None:
        error = UnsupportedClientVersionMapperError(
            "Unsupported client version",
            app_version="26.25.0",
        )
        mapper = SimpleNamespace(
            phone="79990000000",
            request_code=AsyncMock(side_effect=error),
        )

        with self.assertRaises(UnsupportedClientVersionMapperError) as raised:
            await SocketLoginBuildInMappingMethod()._resolve_sms_auth(
                mapper  # type: ignore[arg-type]
            )

        self.assertIs(raised.exception, error)
        mapper.request_code.assert_awaited_once()

    async def test_task_group_preserves_unsupported_version_error(self) -> None:
        manager = LifecycleManager(SimpleNamespace())  # type: ignore[arg-type]
        error = UnsupportedClientVersionMapperError(
            "Unsupported client version",
            app_version="26.25.0",
        )

        async def observe() -> None:
            await asyncio.Event().wait()

        async def connect() -> None:
            raise error

        with self.assertRaises(UnsupportedClientVersionMapperError) as raised:
            await manager._observe_task(observe, connect)

        self.assertIs(raised.exception, error)

    async def test_task_group_prioritizes_unsupported_over_transport_error(
        self,
    ) -> None:
        manager = LifecycleManager(SimpleNamespace())  # type: ignore[arg-type]
        error = UnsupportedClientVersionMapperError(
            "Unsupported client version",
            app_version="26.25.0",
        )
        both_started = asyncio.Event()
        started = 0

        async def fail_together(exception: Exception) -> None:
            nonlocal started
            started += 1
            if started == 2:
                both_started.set()
            await both_started.wait()
            raise exception

        async def observe() -> None:
            await fail_together(RuntimeError("socket closed"))

        async def connect() -> None:
            await fail_together(error)

        with self.assertRaises(UnsupportedClientVersionMapperError) as raised:
            await manager._observe_task(observe, connect)

        self.assertIs(raised.exception, error)

    async def test_transport_close_does_not_mask_pending_version_error(self) -> None:
        mapper = SimpleNamespace(_authorized=asyncio.Event())
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        error = UnsupportedClientVersionMapperError(
            "Unsupported client version",
            app_version="26.25.0",
        )
        await manager._next_generation()

        async def connect() -> None:
            manager.notify_about_exception(
                RuntimeError("socket closed"),
                generation=1,
                source="reader",
            )
            await asyncio.sleep(0)
            raise error

        with self.assertRaises(UnsupportedClientVersionMapperError) as raised:
            await manager._observe_task(manager._observe_auth_error, connect)

        self.assertIs(raised.exception, error)

    async def test_establish_connection_propagates_version_error_before_close(
        self,
    ) -> None:
        error = UnsupportedClientVersionMapperError(
            "Unsupported client version",
            app_version="26.25.0",
        )
        response_ready: asyncio.Future[None] = (
            asyncio.get_running_loop().create_future()
        )
        login_started = asyncio.Event()

        async def login(**_kwargs: object) -> None:
            login_started.set()
            await response_ready
            raise error

        async def slow_close(_exception: Exception | None = None) -> None:
            await asyncio.sleep(1)

        mapper = SimpleNamespace(
            _authorized=asyncio.Event(),
            _protocol_connected=asyncio.Event(),
            logged=False,
            token=None,
            user_agent=object(),
            connect=AsyncMock(),
            login=login,
            close=AsyncMock(side_effect=slow_close),
        )
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        await manager._next_generation()

        async def establish() -> None:
            await manager._establish_connection(
                Mock(),
                close_firstly=False,
            )

        async def deliver_response_and_close_transport() -> None:
            await login_started.wait()
            response_ready.set_result(None)
            manager.notify_about_exception(
                RuntimeError("socket closed"),
                generation=1,
                source="reader",
            )

        delivery = asyncio.create_task(deliver_response_and_close_transport())
        try:
            with self.assertRaises(UnsupportedClientVersionMapperError) as raised:
                await manager._observe_task(manager._observe_auth_error, establish)
        finally:
            await delivery

        self.assertIs(raised.exception, error)
        mapper.close.assert_not_awaited()

    async def test_auth_observer_ignores_previous_attempt_failure(self) -> None:
        mapper = SimpleNamespace(_authorized=asyncio.Event())
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        previous_generation = await manager._next_generation()
        current_generation = await manager._next_generation()
        observer = asyncio.create_task(manager._observe_auth_error())

        manager.notify_about_exception(
            RuntimeError("stale socket failure"),
            generation=previous_generation,
            source="reader",
        )
        await asyncio.sleep(0)
        self.assertFalse(observer.done())

        current_error = RuntimeError("current socket failure")
        manager.notify_about_exception(
            current_error,
            generation=current_generation,
            source="reader",
        )

        with self.assertRaises(MapperLifecycleError) as raised:
            await observer

        self.assertIs(raised.exception.__cause__, current_error)

    async def test_authorize_allocates_generation_for_every_attempt(self) -> None:
        mapper = SimpleNamespace(_authorized=asyncio.Event())
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        observed_generations: list[int] = []

        async def observe_attempt(**_kwargs: object) -> None:
            observed_generations.append(await manager.get_generation())
            if len(observed_generations) == 1:
                raise MapperRestartCycleError("failed attempt")

        with patch.object(manager, "_observe_task", side_effect=observe_attempt):
            with self.assertRaises(MapperRestartCycleError):
                await manager._authorize(None, Mock())
            await manager._authorize(None, Mock())

        self.assertEqual(observed_generations, [1, 2])

    async def test_transport_maps_unsupported_version_error(self) -> None:
        response = Envelope(
            seq=1,
            cmd=3,
            opcode=17,
            payload={
                "error": ErrorCode.UNSUPPORTED_CLIENT_VERSION,
                "message": "Unsupported client version",
            },
        )
        response_future = asyncio.get_running_loop().create_future()
        response_future.set_result(response)
        target = SimpleNamespace(
            protocol=SimpleNamespace(send=AsyncMock(return_value=response_future)),
            user_agent=SimpleNamespace(app_version="26.25.0"),
            _logger=logging.getLogger("UnsupportedClientVersionTest"),
        )

        with self.assertRaises(UnsupportedClientVersionMapperError) as raised:
            await TransportMixin.send_raw(  # type: ignore[arg-type]
                target,
                method=Mock(),
                check_errors=True,
            )

        self.assertEqual(
            raised.exception.error,
            ErrorCode.UNSUPPORTED_CLIENT_VERSION,
        )
        self.assertEqual(raised.exception.message, "Unsupported client version")
        self.assertEqual(raised.exception.app_version, "26.25.0")
        self.assertFalse(
            hasattr(UnsupportedClientVersionMapperError, "error_code")
        )

    async def test_lifecycle_emits_event_rotates_version_and_reconnects(self) -> None:
        version_events: list[UnsupportedClientVersionEvent] = []
        disconnect_events = []
        error = UnsupportedClientVersionMapperError(
            "Unsupported client version",
            app_version="26.25.0",
        )

        class Api:
            app_version = "26.25.0"

            async def get_available_app_versions(self) -> tuple[str, ...]:
                return ("26.25.0", "26.35.1")

            async def _emit_unsupported_version(
                self,
                event: UnsupportedClientVersionEvent,
            ) -> None:
                version_events.append(event)

            async def set_random_app_version(self, **kwargs: object) -> str:
                self.app_version = "26.35.1"
                return self.app_version

            async def _emit_disconnect(self, event: object) -> None:
                disconnect_events.append(event)

        mapper = SimpleNamespace(
            max_api=Api(),
            extra_config=SimpleNamespace(
                reconnect=True,
                reconnect_delay=1.0,
                relogin=True,
                autochange_app_version_if_current_unsupported=True,
            ),
            close=AsyncMock(),
        )
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        manager._authorize = AsyncMock(  # type: ignore[method-assign]
            side_effect=[error, None]
        )

        with patch(
            "pyromax.mapping.envelope.v11.LifecycleManager.asyncio.sleep",
            new=AsyncMock(),
        ):
            await manager._authorize_cycle(None, Mock())

        self.assertEqual(manager._authorize.await_count, 2)
        self.assertEqual(len(version_events), 1)
        self.assertIs(version_events[0].exception, error)
        self.assertEqual(version_events[0].app_version, "26.25.0")
        self.assertEqual(len(disconnect_events), 1)
        self.assertIs(disconnect_events[0].exception, error)

    async def test_version_handler_choice_disables_automatic_rotation(self) -> None:
        error = UnsupportedClientVersionMapperError(
            "Unsupported client version",
            app_version="26.25.0",
        )

        class Api:
            app_version = "26.25.0"

            async def get_available_app_versions(self) -> tuple[str, ...]:
                return ("26.25.0", "26.35.1")

            async def _emit_unsupported_version(
                self,
                _event: UnsupportedClientVersionEvent,
            ) -> None:
                self.app_version = "26.35.1"

            set_random_app_version = AsyncMock()

        api = Api()
        manager = LifecycleManager(  # type: ignore[arg-type]
            SimpleNamespace(max_api=api)
        )

        await manager._handle_unsupported_version(error)

        api.set_random_app_version.assert_not_awaited()


class RuntimeAppVersionApiTest(unittest.IsolatedAsyncioTestCase):
    def make_api(self) -> MaxApi:
        api = object.__new__(MaxApi)
        config = ExtraConfig(
            mapper=EnvelopeMapperConfigV11(
                device_type=DeviceType.Desktop,
                user_agent_config=DesktopEnvelopeMappingUserAgentConfigV11(),
            ),
            version_api=VersionApi(),
        )
        user_agent = AppUserAgentMappingModel.get_random_user_agent(
            **config.mapper.user_agent_config.model_dump()
        )
        mapper = SimpleNamespace(
            mapper_config=config.mapper,
            user_agent=user_agent,
            fingerprint_generator=SimpleNamespace(data={}),
            reconnect_for_app_version_change=AsyncMock(),
        )
        mapper.apply_app_version = lambda version, fingerprint: (
            ConstructorMixin.apply_app_version(mapper, version, fingerprint)
        )

        api.extra_config = config
        api.mapper = mapper  # type: ignore[assignment]
        api.device_type = DeviceType.Desktop
        api.token_suffix = "MaxApi"
        api.session = SessionInfo(
            session_id="session",
            token=None,
            device_id=user_agent.device_id,
            phone=None,
            user_agent_config=config.mapper.user_agent_config.to_string(),
        )
        api._session_updates_queue = asyncio.Queue()
        api._app_version_lock = asyncio.Lock()
        return api

    async def test_sets_specific_version_pair_and_requests_reconnect(self) -> None:
        api = self.make_api()

        async def reconnect_without_version_lock(_app_version: str) -> None:
            self.assertFalse(api._app_version_lock.locked())

        api.mapper.reconnect_for_app_version_change.side_effect = (  # type: ignore[attr-defined]
            reconnect_without_version_lock
        )

        selected = await api.set_app_version("26.35.1")

        expected = VersionApi().resolve("26.35.1")
        self.assertEqual(selected, "26.35.1")
        self.assertEqual(api.app_version, "26.35.1")
        self.assertEqual(api.mapper.user_agent.app_version, "26.35.1")  # type: ignore[attr-defined]
        self.assertEqual(  # type: ignore[attr-defined]
            api.mapper.user_agent.build_number,
            expected.build_number,
        )
        api.mapper.reconnect_for_app_version_change.assert_awaited_once_with(  # type: ignore[attr-defined]
            "26.35.1"
        )

    async def test_sets_random_alternative_version(self) -> None:
        api = self.make_api()

        with patch("pyromax.core.client.secrets.choice", return_value="26.35.1"):
            selected = await api.set_random_app_version(reconnect=False)

        self.assertEqual(selected, "26.35.1")
        self.assertEqual(api.app_version, "26.35.1")
        api.mapper.reconnect_for_app_version_change.assert_not_awaited()  # type: ignore[attr-defined]
