from __future__ import annotations
import asyncio
from asyncio import Task, Lock, Event
import logging
from typing import TYPE_CHECKING, Any, _ProtocolMeta, TypeVar
from collections.abc import Callable, Coroutine

from typing import cast, Protocol

from .....config import ExtraConfig, EnvelopeMapperConfigV11
from .....mixins import AsyncInitializerMixin, AsyncConstructorMeta
from .....protocol import EnvelopeProtocol
from ..payloads.models import BaseUserAgentMappingModel
from ..constants import DEVICE_TYPE_TO_USERAGENT_MODEL as DEVICE_TYPE_TO_USER_AGENT_MAP
from ..LifecycleManager import LifecycleManager
from ..telemetry import TelemetryManager
from .....utils import FingerprintGenerator, write_token, read_token, hide_func_call

if TYPE_CHECKING:
    from .....core import MaxApi
    from ..Mapper import Mapper
    from .....models import RegistrationConfig, BaseMaxObject

T = TypeVar("T", bound="BaseMaxObject")


from .MixinProtocol import MixinProtocol

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

        self.max_api: MaxApi | None = None
        # self.token: str | None = self.mapper_config.token

        self.password: str | None = self.mapper_config.password
        self.phone: str | None = self.mapper_config.phone
        self.sms_auth = self.mapper_config.sms_auth
        self.request_timeout: float = self.mapper_config.request_timeout
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

        self.fingerprint_generator = FingerprintGenerator()
        self.logged: bool = False
        self.calls_seed: int | None = None

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
            url_callback=self.mapper_config.url_callback,
            registration_config=self.mapper_config.registration_config,
            use_mobile_fingerprint=self.mapper_config.use_mobile_fingerprint,
        )

        await self._protocol_connected.wait()

        self._logger.info("Mapper initialized")

    async def stop(self) -> None:
        await self.close()
        if self._lifecycle_manager is not None:
            await self._lifecycle_manager.stop()
        self._lifecycle_manager_inited.clear()
        self._telemetry = None
        self.protocol.set_generation_getter(None)
        self.protocol.set_exceptions_callback(None)

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
