from __future__ import annotations
from typing import Protocol, TYPE_CHECKING, Any
import logging

if TYPE_CHECKING:
    import asyncio
    from collections.abc import Coroutine, Callable
    from ..payloads.models import BaseUserAgentMappingModel
    from .....protocol import EnvelopeProtocol, Envelope
    from .....core import MaxApi
    from ..LifecycleManager import LifecycleManager


class MixinProtocol(Protocol):
    token: str | None
    password: str | None
    phone: str | None
    TOKEN_NAME: str
    max_api: MaxApi | None
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