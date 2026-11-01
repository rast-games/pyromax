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

        async def connect() -> None:
            raise error

        with self.assertRaises(UnsupportedClientVersionMapperError) as raised:
            await manager._observe_task(connect())

        self.assertIs(raised.exception, error)

    async def test_task_group_prioritizes_unsupported_over_transport_error(
        self,
    ) -> None:
        manager = LifecycleManager(SimpleNamespace())  # type: ignore[arg-type]
        error = UnsupportedClientVersionMapperError(
            "Unsupported client version",
            app_version="26.25.0",
        )
        async def connect() -> None:
            manager.notify_about_exception(
                RuntimeError("socket closed"),
                generation=0,
                source="reader",
            )
            await asyncio.sleep(0)
            raise error

        with self.assertRaises(UnsupportedClientVersionMapperError) as raised:
            await manager._observe_task(connect())

        self.assertIs(raised.exception, error)

    async def test_transport_close_does_not_mask_pending_version_error(self) -> None:
        mapper = SimpleNamespace(_authorized=asyncio.Event())
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        error = UnsupportedClientVersionMapperError(
            "Unsupported client version",
            app_version="26.25.0",
        )
        manager._next_generation()

        async def connect() -> None:
            manager.notify_about_exception(
                RuntimeError("socket closed"),
                generation=1,
                source="reader",
            )
            await asyncio.sleep(0)
            raise error

        with self.assertRaises(UnsupportedClientVersionMapperError) as raised:
            await manager._observe_task(connect())

        self.assertIs(raised.exception, error)

    async def test_observer_propagates_version_error_without_extra_close(self) -> None:
        error = UnsupportedClientVersionMapperError(
            "Unsupported client version",
            app_version="26.25.0",
        )
        mapper = SimpleNamespace(close=AsyncMock())
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]

        async def authorize() -> None:
            manager.notify_about_exception(
                RuntimeError("socket closed"),
                generation=0,
                source="reader",
            )
            await asyncio.sleep(0)
            raise error

        with self.assertRaises(UnsupportedClientVersionMapperError) as raised:
            await manager._observe_task(authorize())

        self.assertIs(raised.exception, error)
        mapper.close.assert_not_awaited()

    async def test_auth_observer_ignores_previous_attempt_failure(self) -> None:
        mapper = SimpleNamespace(_authorized=asyncio.Event())
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]
        previous_generation = manager._next_generation()
        current_generation = manager._next_generation()
        observer = asyncio.create_task(manager._observe_error())

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

        with self.assertRaises(RuntimeError) as raised:
            await observer

        self.assertIs(raised.exception, current_error)

    async def test_authorize_allocates_generation_for_every_attempt(self) -> None:
        manager: LifecycleManager
        observed_generations: list[int] = []

        class Mapper:
            logged = True
            _telemetry = None

            async def close(self, _exception: Exception | None = None) -> None:
                return None

            async def connect(self) -> None:
                observed_generations.append(manager.get_generation())

            async def _send_user_agent(self) -> None:
                return None

            async def _send_auth_token(self) -> None:
                if len(observed_generations) == 1:
                    raise MapperRestartCycleError("failed attempt")

        mapper = Mapper()
        manager = LifecycleManager(mapper)  # type: ignore[arg-type]

        with self.assertRaises(MapperRestartCycleError):
            await manager._authorize()
        await manager._authorize()

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
        self.assertFalse(hasattr(UnsupportedClientVersionMapperError, "error_code"))

    async def test_handler_emits_event_and_rotates_version(self) -> None:
        version_events: list[UnsupportedClientVersionEvent] = []
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

        target = SimpleNamespace(
            max_api=Api(),
            _unsupported_app_versions=set(),
            _logger=logging.getLogger("UnsupportedClientVersionTest"),
            extra_config=SimpleNamespace(
                autochange_app_version_if_current_unsupported=True,
            ),
        )

        await ConstructorMixin._handle_unsupported_version(  # type: ignore[arg-type]
            target,
            error,
        )

        self.assertEqual(len(version_events), 1)
        self.assertIs(version_events[0].exception, error)
        self.assertEqual(version_events[0].app_version, "26.25.0")
        self.assertEqual(target.max_api.app_version, "26.35.1")
        self.assertEqual(target._unsupported_app_versions, {"26.25.0"})

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
        target = SimpleNamespace(
            max_api=api,
            _unsupported_app_versions=set(),
            _logger=logging.getLogger("UnsupportedClientVersionTest"),
            extra_config=SimpleNamespace(
                autochange_app_version_if_current_unsupported=True,
            ),
        )

        await ConstructorMixin._handle_unsupported_version(  # type: ignore[arg-type]
            target,
            error,
        )

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
