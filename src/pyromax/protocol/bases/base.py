from __future__ import annotations

from abc import abstractmethod
from asyncio import Event
from collections.abc import Awaitable, Iterable
from typing import Any, TYPE_CHECKING

from src.pyromax.mixins import AsyncInitializerMixin
if TYPE_CHECKING:
    from src.pyromax import BaseMaxProtocolMethod

class BaseMaxProtocol(AsyncInitializerMixin):
    running: Event
    failed: Event

    @abstractmethod
    async def send(self, method: BaseMaxProtocolMethod, data: Any) -> Awaitable: pass


    @abstractmethod
    async def get_updates(self) -> Iterable: pass