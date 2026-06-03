from __future__ import annotations
import asyncio
from asyncio import Task, Lock, Event
import logging
from typing import TYPE_CHECKING, Any
from collections.abc import Callable, Coroutine
from typing import cast

from .....mixins import AsyncInitializerMixin
from .....protocol import EnvelopeProtocol
from ..payloads.models import BaseUserAgentMappingModel
from ..constants import DEVICE_TYPE_TO_USERAGENT_MODEL as DEVICE_TYPE_TO_USER_AGENT_MAP
from ..LifecycleManager import LifecycleManager

if TYPE_CHECKING:
    from .....core import MaxApi
    from ..Mapper import Mapper

from .MixinProtocol import MixinProtocol

class ConstructorMixin(AsyncInitializerMixin, MixinProtocol):

    def __init__(
            self,
            protocol: EnvelopeProtocol,
            keepalive_ping_interval: int,
    ) -> None:
        self.protocol = protocol
        self.protocol_version = 11
        self._keepalive_ping_interval = keepalive_ping_interval
        self._logger = logging.getLogger('MapperV11')
        self._keepalive_task: Task[Any] | None = None
        self.keep_alive_interactive: bool = True
        self._update_listener_task: Task[Any] | None = None
        self.token: str | None = None
        self.TOKEN_NAME = 'ENVELOPE_MAX_TOKEN_V11' + self.protocol.transport.__class__.__name__
        self.max_api: MaxApi | None = None
        self._manage_lifecycle_task: Task[Any] | None = None
        self._update_listener_lock: Lock = Lock()
        self._authorized = asyncio.Event()
        self.user_agent: BaseUserAgentMappingModel | None = None
        self.logged: bool = False
        self.password: str | None = None
        self.phone: str | None = None
        self.sms_auth = False
        self._lifecycle_manager_inited: asyncio.Event = Event()
        self._mapper_connected: asyncio.Event = Event()

        self._lifecycle_manager: LifecycleManager | None = None


    @property
    def DEVICE_TYPE_TO_USERAGENT_MODEL(self) -> dict[str, type[BaseUserAgentMappingModel]]:
        return DEVICE_TYPE_TO_USER_AGENT_MAP


    async def _async_init(
            self,
            max_api: MaxApi,
            protocol: EnvelopeProtocol,
            *args: Any,
            keepalive_ping_interval: int = 30,
            **kwargs: Any,
    ) -> None:
        from .....core import MaxApi
        if not isinstance(max_api, MaxApi):
            raise TypeError('max_api must be an instance of MaxApi')
        if not isinstance(protocol, EnvelopeProtocol):
            raise TypeError("protocol must be an instance of EnvelopeProtocol")
        await asyncio.to_thread(self.__init__, protocol=protocol, keepalive_ping_interval=keepalive_ping_interval) # type: ignore[misc]
        self.max_api = max_api



    async def initialize_client(
            self,
            token: str | None = None,
            device_id: str | None = None,
            protocol_version: int = 11,
            device_type: str = 'WEB',
            password: str | None = None,
            phone: str | None = None,
            sms_auth: bool = False,
            interactive: bool = True,
            keep_alive_interactive: bool | None = None,
            url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
            connection_timeout: int | None = None,
            **kwargs: Any
    ) -> None:
        if device_type not in self.DEVICE_TYPE_TO_USERAGENT_MODEL:
            raise RuntimeError(f'Unknown device type: {device_type}')
        user_agent_model = self.DEVICE_TYPE_TO_USERAGENT_MODEL[device_type]
        user_agent = user_agent_model(device_type=device_type)
        self.user_agent = user_agent
        if token is None:
            from .....utils import read_token
            token = await read_token(
                name_of_token=self.TOKEN_NAME
            )
        self.token = token
        self.password = password
        self.phone = phone
        self.sms_auth = sms_auth
        if keep_alive_interactive is None:
            keep_alive_interactive = interactive
        self.keep_alive_interactive = keep_alive_interactive
        self.protocol_version = protocol_version
        from ..Mapper import Mapper
        self._lifecycle_manager = LifecycleManager(
            mapper=cast(Mapper, self),
            connect_timeout=connection_timeout
        )

        if self._lifecycle_manager is None:
            raise RuntimeError('Cannot create a new lifecycle manager')

        self.protocol.set_generation_getter(self._lifecycle_manager.get_generation)
        self.protocol.set_exceptions_callback(self._lifecycle_manager.notify_about_exception)
        self._lifecycle_manager_inited.set()

        self._lifecycle_manager.start(url_callback=url_callback)
        self._logger.info("Mapper initialized")