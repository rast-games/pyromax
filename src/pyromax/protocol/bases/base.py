from abc import abstractmethod
from asyncio import Event
from collections.abc import Awaitable, AsyncGenerator, Iterable
from typing import Any

from src.pyromax.mixins import AsyncInitializerMixin
from .request_response import Request, Response


class BaseMaxProtocol(AsyncInitializerMixin):
    running: Event
    failed: Event

    @abstractmethod
    async def send(self, method, data: Any) -> Awaitable: pass


    @abstractmethod
    async def get_updates(self) -> Iterable: pass

    # @abstractmethod
    # async def connect(self) -> None: pass


    # @abstractmethod
    # async def close(self) -> None: pass


