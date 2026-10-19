from __future__ import annotations
import asyncio
from asyncio import Task, Lock, Event
import logging
import threading
import time
from typing import TYPE_CHECKING, Any, _ProtocolMeta, TypeVar

from typing import cast

from .....config import ExtraConfig, EnvelopeMapperConfigV11
from .....mixins import AsyncInitializerMixin, AsyncConstructorMeta
from .....protocol import EnvelopeProtocol
from ..payloads.models import BaseUserAgentMappingModel
from ..constants import DEVICE_TYPE_TO_USERAGENT_MODEL as DEVICE_TYPE_TO_USER_AGENT_MAP
from ..LifecycleManager import LifecycleManager
from ..telemetry import TelemetryManager
from .....utils import CircuitBreaker, FingerprintGenerator, hide_func_call
from .....interaction import AuthInteractor
from .....exceptions import RestartMapperError
from .MixinProtocol import MixinProtocol

if TYPE_CHECKING:
    from .....core import MaxApi
    from .....models import ApkBuildFingerprint, BaseMaxObject

T = TypeVar("T", bound="BaseMaxObject")

# ProtocolMeta: type = type(Protocol)


class AsyncInitializerMixinProtocol(AsyncConstructorMeta, _ProtocolMeta):
    pass


class ConstructorMixin(
    AsyncInitializerMixin, MixinProtocol, metaclass=AsyncInitializerMixinProtocol
):

    def __init__(
        self,
        protocol: EnvelopeProtocol,
        extra_config: ExtraConfig,
    ) -> None:
        """Initialize the constructor mixin.

        :param protocol: Protocol backend or protocol instance.
        :type protocol: EnvelopeProtocol
        :param keepalive_ping_interval: The keepalive ping interval value.
        :type keepalive_ping_interval: int
        """
        mapper_config = extra_config.mapper
        if not isinstance(mapper_config, EnvelopeMapperConfigV11):
            raise TypeError(
                "mapper config must be an instance of EnvelopeMappingConfigV11 for this mapper"
            )
        self.extra_config = extra_config
        self.mapper_config: EnvelopeMapperConfigV11 = mapper_config

        if self.mapper_config.device_type not in self.DEVICE_TYPE_TO_USERAGENT_MODEL:
            raise RuntimeError(f"Unknown device type: {self.mapper_config.device_type}")

        self.protocol: EnvelopeProtocol
        self.protocol_version: int

        self.max_api = cast("MaxApi", None)
        # self.token: str | None = self.mapper_config.token

        self.password: str | None = self.mapper_config.password
        if not isinstance(extra_config.auth_interactor, AuthInteractor):
            raise TypeError(
                "EnvelopeV11 mapper requires an AuthInteractor-compatible auth_interactor"
            )
        self.phone: str | None = self.mapper_config.phone
        self.sms_auth = self.mapper_config.sms_auth
        self.request_timeout: float = self.mapper_config.request_timeout
        circuit_breakers_config = self.mapper_config.circuit_breakers
        transport_config = circuit_breakers_config.transport
        api_config = circuit_breakers_config.api
        self._transport_circuit_breaker = (
            CircuitBreaker(
                failure_threshold=transport_config.failure_threshold,
                recovery_timeout=transport_config.recovery_timeout,
                max_cycles=transport_config.max_cycles,
                backoff_factor=transport_config.backoff_factor,
                max_recovery_timeout=transport_config.max_recovery_timeout,
                wait_when_open=transport_config.wait_when_open,
                name="transport",
            )
            if transport_config.enabled
            else None
        )
        self._api_circuit_breaker = (
            CircuitBreaker(
                failure_threshold=api_config.failure_threshold,
                recovery_timeout=api_config.recovery_timeout,
                max_cycles=api_config.max_cycles,
                backoff_factor=api_config.backoff_factor,
                max_recovery_timeout=api_config.max_recovery_timeout,
                wait_when_open=api_config.wait_when_open,
                name="api",
            )
            if api_config.enabled
            else None
        )
        self.use_telemetry: bool = self.mapper_config.use_telemetry
        self.keep_alive_interactive: bool = self.mapper_config.interactive
        self.connect_timeout = self.mapper_config.connect_timeout

        user_agent_params = self.mapper_config.user_agent_config.model_dump()
        user_agent_model = self.DEVICE_TYPE_TO_USERAGENT_MODEL[
            self.mapper_config.device_type
        ]
        user_agent = user_agent_model.get_random_user_agent(**user_agent_params)
        self.user_agent = user_agent

        # self.TOKEN_NAME: str

        fingerprint_overrides = None
        app_version = getattr(self.mapper_config.user_agent_config, "app_version", None)
        if (
            self.mapper_config.user_agent_config.supports_app_fingerprint
            and app_version is not None
            and extra_config.app_fingerprint is not None
        ):
            fingerprint_overrides = {
                app_version: extra_config.app_fingerprint,
            }
        self.fingerprint_generator = FingerprintGenerator(fingerprint_overrides)
        self.logged: bool = False
        self.calls_seed: int | None = None
        self._previous_cid = 0
        self._cid_lock = threading.Lock()

        # self._update_listener_task: Task[Any] | None = None

        self._update_listener_lock: Lock = Lock()
        self._authorized = asyncio.Event()

        self._keepalive_task: Task[Any] | None = None
        self._keepalive_ping_interval = self.mapper_config.keepalive_ping_interval

        self._mapper_connected: asyncio.Event = Event()
        self._protocol_connected: asyncio.Event = Event()

        self._lifecycle_manager: LifecycleManager | None = None
        self._lifecycle_manager_inited: asyncio.Event = Event()

        self._telemetry: TelemetryManager | None = None
        self._logger = self.mapper_config.mapper_logger or logging.getLogger(
            "MapperV11"
        )

        # self.user_agent: BaseUserAgentMappingModel | None = None

    def _next_cid(self) -> int:
        """Return a per-mapper CID that strictly increases in milliseconds."""
        with self._cid_lock:
            now = int(time.time() * 1000)
            cid = max(now, self._previous_cid + 1)
            self._previous_cid = cid
            return cid

    @property
    def auth_interactor(self) -> AuthInteractor:
        """Return the auth interactor from the shared client configuration."""
        interactor = self.extra_config.auth_interactor
        if not isinstance(interactor, AuthInteractor):
            raise TypeError("auth_interactor must implement AuthInteractor")
        return interactor

    @property
    def transport_circuit_breaker(self) -> CircuitBreaker | None:
        """Return the mapper transport circuit breaker, if enabled."""
        return self._transport_circuit_breaker

    @property
    def api_circuit_breaker(self) -> CircuitBreaker | None:
        """Return the mapper API circuit breaker, if enabled."""
        return self._api_circuit_breaker

    @property
    def DEVICE_TYPE_TO_USERAGENT_MODEL(
        self,
    ) -> dict[str, type[BaseUserAgentMappingModel]]:
        """D e v i c e t y p e t o u s e r a g e n t m o d e l.

        :returns: The resulting dict[str, type[BaseUserAgentMappingModel]] value.
        :rtype: dict[str, type[BaseUserAgentMappingModel]]
        """
        return DEVICE_TYPE_TO_USER_AGENT_MAP

    async def _async_init(
        self,
        max_api: MaxApi,
        protocol: EnvelopeProtocol,
        extra_config: ExtraConfig,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Async init.

        :param max_api: MAX client to bind or use.
        :type max_api: MaxApi
        :param protocol: Protocol backend or protocol instance.
        :type protocol: EnvelopeProtocol
        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param keepalive_ping_interval: The keepalive ping interval value.
        :type keepalive_ping_interval: int
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :raises TypeError: If max_api must be an instance of MaxApi.
        :raises TypeError: If protocol must be an instance of EnvelopeProtocol.
        """
        from .....core import MaxApi

        mapper_config = extra_config.mapper
        if not isinstance(mapper_config, EnvelopeMapperConfigV11):
            raise TypeError(
                "mapper config must be an instance of EnvelopeMappingConfigV11 for this mapper"
            )
        conf: EnvelopeMapperConfigV11 = mapper_config

        self.protocol = protocol
        self.protocol_version = conf.protocol_version

        if conf.device_type not in self.DEVICE_TYPE_TO_USERAGENT_MODEL:
            raise RuntimeError(f"Unknown device type: {self.mapper_config.device_type}")

        if not isinstance(max_api, MaxApi):
            raise TypeError("max_api must be an instance of MaxApi")
        if not isinstance(protocol, EnvelopeProtocol):
            raise TypeError("protocol must be an instance of EnvelopeProtocol")

        # token = max_api.token or conf.token

        # extra_config.mapper.token = token

        hide_func_call(
            type(self).__init__,
            self,
            protocol=protocol,
            extra_config=extra_config,
        )

        self.max_api = max_api

    @property
    def token(self) -> str | None:
        return self.max_api.token

    @token.setter
    def token(self, token: str | None) -> None:
        self.max_api.token = token

    async def start(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Start client."""

        from ..Mapper import Mapper

        self._lifecycle_manager = LifecycleManager(
            mapper=cast(Mapper, self),
            connect_timeout=self.connect_timeout,
            need_login=self.max_api.token is None,
        )

        if self._lifecycle_manager is None:
            raise RuntimeError("Cannot create a new lifecycle manager")

        if self.use_telemetry:
            if self.max_api is None:
                raise RuntimeError("Mapper not bounded to MaxApi instance")
            self._telemetry = TelemetryManager(
                max_api=self.max_api,
                mapper=cast(Mapper, self),
            )

        self.protocol.set_generation_getter(self._lifecycle_manager.get_generation)
        self.protocol.set_exceptions_callback(
            self._lifecycle_manager.notify_about_exception
        )
        self._lifecycle_manager_inited.set()

        self._lifecycle_manager.start(
            registration_config=self.mapper_config.registration_config,
            use_mobile_fingerprint=self.mapper_config.use_mobile_fingerprint,
        )

        await self._lifecycle_manager.wait_until_connected()

        self._logger.info("Mapper initialized")

    async def stop(self) -> None:
        if self._lifecycle_manager is not None:
            await self._lifecycle_manager.stop()
        else:
            await self.close()
        self._protocol_connected.clear()
        self._lifecycle_manager_inited.clear()
        self._telemetry = None
        self.protocol.set_generation_getter(None)
        self.protocol.set_exceptions_callback(None)

    async def wait_until_ready(self) -> None:
        """Wait until the current connection is authorized."""
        await self._authorized.wait()

    def apply_app_version(
        self,
        app_version: str,
        fingerprint: ApkBuildFingerprint,
    ) -> None:
        """Update the configured and live user-agent version as one pair."""
        config = self.mapper_config.user_agent_config
        update: dict[str, Any] = {"app_version": app_version}
        if "build_number" in type(config).model_fields:
            update["build_number"] = fingerprint.build_number
        self.mapper_config.user_agent_config = config.model_copy(update=update)

        user_agent = self.user_agent
        if user_agent is not None:
            live_update = {
                key: value
                for key, value in update.items()
                if key in type(user_agent).model_fields
            }
            self.user_agent = user_agent.model_copy(update=live_update)

        self.fingerprint_generator.data[app_version] = fingerprint

    async def reconnect_for_app_version_change(self, app_version: str) -> None:
        """Reconnect so the newly selected version is sent to MAX."""
        lifecycle_manager = self._lifecycle_manager
        if lifecycle_manager is None or not self._protocol_connected.is_set():
            return
        await lifecycle_manager.request_reconnect(
            RestartMapperError(f"Application version changed to {app_version}")
        )

    def bind_api_instance(self, obj: T) -> T:
        """Bind api instance.

        :param obj: T instance to process.
        :type obj: T
        :returns: The resulting T value.
        :rtype: T
        :raises RuntimeError: If cannot bind api instance without max_api.
        """
        if self.max_api is None:
            raise RuntimeError("Cannot bind api instance without max_api")

        obj.as_(self.max_api)
        return obj
