from __future__ import annotations
from typing import Protocol, TYPE_CHECKING, Any, TypeVar
import logging

from ..telemetry import TelemetryManager

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Coroutine, Callable, Mapping
    from ..payloads.models import BaseUserAgentMappingModel
    from .....protocol import EnvelopeProtocol, Envelope
    from .....core import MaxApi
    from ..LifecycleManager import LifecycleManager
    from .....utils import FingerprintGenerator
    from .....config import EnvelopeMapperConfigV11, ExtraConfig
    from .....models import BaseMaxObject
    from .....models.Chat import Chat
    from .....models.Contact import Contact


T = TypeVar("T", bound="BaseMaxObject")
T_CHAT = TypeVar("T_CHAT", bound="Chat")
T_USER = TypeVar("T_USER", bound="Contact")


class MixinProtocol(Protocol):
    mapper_config: EnvelopeMapperConfigV11
    extra_config: ExtraConfig
    token: str | None
    password: str | None
    phone: str | None
    fingerprint_generator: FingerprintGenerator
    # TOKEN_NAME: str
    max_api: MaxApi | None
    logged: bool
    user_agent: BaseUserAgentMappingModel | None
    _resolve_two_factor: Callable[..., Coroutine[Any, Any, Any]]
    sms_auth: bool
    _call_build_in_method: Callable[..., Coroutine[Any, Any, Any]]
    _authorized: asyncio.Event
    protocol: EnvelopeProtocol
    _keepalive_ping_interval: int
    keep_alive_interactive: bool
    _keepalive_task: asyncio.Task[Any] | None
    send: Callable[..., Coroutine[Any, Any, Envelope]]
    send_raw: Callable[..., Coroutine[Any, Any, Envelope]]
    send_raw_with_running_wait: Callable[..., Coroutine[Any, Any, Envelope]]
    _logger: logging.Logger
    _keepalive: Callable[..., Coroutine[Any, Any, Any]]
    _lifecycle_manager: LifecycleManager | None
    _lifecycle_manager_inited: asyncio.Event
    _mapper_connected: asyncio.Event
    _protocol_connected: asyncio.Event
    _telemetry: TelemetryManager | None

    async def close(self, pending_requests_exc: Exception | None = None) -> None: ...

    # DEVICE_TYPE_TO_USERAGENT_MODEL: dict[str, type[BaseUserAgentMappingModel]]

    @property
    def DEVICE_TYPE_TO_USERAGENT_MODEL(
        self,
    ) -> Mapping[str, type[BaseUserAgentMappingModel]]: ...

    def bind_api_instance(self, obj: T) -> T:
        """Bind api instance.

        :param obj: T instance to process.
        :type obj: T
        :returns: The resulting T value.
        :rtype: T
        """
        ...

    def _cache_chat(self, chat: T_CHAT) -> T_CHAT:
        """Cache chat.

        :param chat: T_CHAT instance to process.
        :type chat: T_CHAT
        :returns: The resulting T_CHAT value.
        :rtype: T_CHAT
        """
        ...

    def _cache_user(self, user: T_USER) -> T_USER:
        """Cache user.

        :param user: T_USER instance to process.
        :type user: T_USER
        :returns: The resulting T_USER value.
        :rtype: T_USER
        """
        ...
