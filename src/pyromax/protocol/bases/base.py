from __future__ import annotations

from abc import abstractmethod
from asyncio import Event
from collections.abc import Awaitable, Iterable
from typing import Any, TYPE_CHECKING

from ...mixins import AsyncInitializerMixin
if TYPE_CHECKING:
    from .methods import BaseMaxProtocolMethod
    from ...transtport import BaseTransport

class BaseMaxProtocol(AsyncInitializerMixin):
    running: Event
    failed: Event
    transport: BaseTransport

    @abstractmethod
    async def send(self, method: BaseMaxProtocolMethod, data: Any) -> Awaitable: pass


    @abstractmethod
    async def get_updates(self) -> Iterable: pass


    @property
    @abstractmethod
    def transport(self) -> BaseTransport: pass