from __future__ import annotations

from typing import Any, TypeVar, TYPE_CHECKING, TypeAlias
from abc import ABC, abstractmethod
from collections.abc import Callable, Awaitable

from ...models import BaseMaxObject
from ...protocol import Response

if TYPE_CHECKING:
    from ..event import MaxObject

class BaseMiddleware(ABC):
    """
    Generic middleware class
    """

    @abstractmethod
    async def __call__(
        self,
        handler: Callable[[MaxObject, dict[type[Any] | str, Any]], Awaitable[Any]],
        event: MaxObject,
        data: dict[type[Any] | str, Any],
    ) -> Any:
        """
        Execute middleware

        :param handler: Wrapped handler in middlewares chain
        :param event: Incoming event (Subclass of :class:`pyromax.models.base.BaseMaxObject` or :class:`pyromax.protocol.bases.request_response.Response`)
        :param data: Contextual data. Will be mapped to handler arguments
        :return: :class:`Any`
        """



MiddlewareEventType = TypeVar("MiddlewareEventType", bound=BaseMaxObject | Response)

NextMiddlewareType = Callable[[MiddlewareEventType, dict[str, Any]], Awaitable[Any]]

MiddlewareType: TypeAlias = (
    BaseMiddleware
    | Callable[
        [NextMiddlewareType[MiddlewareEventType], MiddlewareEventType, dict[str, Any]],
        Awaitable[Any],
    ]
)