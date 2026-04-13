from __future__ import annotations

from abc import abstractmethod
from asyncio import Event
from collections.abc import Awaitable, Iterable
from typing import Any, TYPE_CHECKING, TypeVar, Generic

from ...mixins import AsyncInitializerMixin
from .request_response import Request, Response
if TYPE_CHECKING:
    from .methods import BaseMaxProtocolMethod
    from ...transport import BaseTransport

T = TypeVar('T', bound=Request[Any], contravariant=True)
R = TypeVar('R', bound=Response, covariant=True)

class BaseMaxProtocol(AsyncInitializerMixin, Generic[T, R]):
    running: Event
    failed: Event

    @abstractmethod
    async def send(self, method: BaseMaxProtocolMethod[T], data: Any | None = None) -> Awaitable[R]: pass


    @abstractmethod
    async def get_updates(self) -> Iterable[Any]: pass


    @property
    @abstractmethod
    def transport(self) -> BaseTransport: pass