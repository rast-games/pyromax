from __future__ import annotations

from typing import Any, TypeVar, TYPE_CHECKING, TypeAlias, Generic
from abc import ABC, abstractmethod
from collections.abc import Callable, Awaitable


if TYPE_CHECKING:
    from ..event import MaxObject


event_type = TypeVar("event_type")
return_type = TypeVar("return_type")


class AbstractMiddleware(ABC, Generic[event_type, return_type]):
    @abstractmethod
    async def __call__(
        self,
        handler: Callable[[event_type, dict[type[Any] | str, Any]], Awaitable[Any]],
        event: event_type,
        data: dict[type[Any] | str, Any],
    ) -> return_type:
        """Process an event through the abstract middleware.

        :param handler: Handler to invoke.
        :type handler: Callable[[event_type, dict[type[Any] | str, Any]], Awaitable[Any]]
        :param event: Incoming event to process.
        :type event: event_type
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[type[Any] | str, Any]
        :returns: The resulting return_type value.
        :rtype: return_type
        """
        ...


class BaseMiddleware(AbstractMiddleware["MaxObject", Any]):
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
        """Execute middleware

        :param handler: Wrapped handler in middlewares chain
        :param event: Incoming event (Subclass of :class:`pyromax.models.base.BaseMaxObject` or :class:`pyromax.protocol.bases.request_response.Response`)
        :param data: Contextual data. Will be mapped to handler arguments
        :return: :class:`Any`

        :type handler: Callable[[MaxObject, dict[type[Any] | str, Any]], Awaitable[Any]]
        :type event: MaxObject
        :type data: dict[type[Any] | str, Any]
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        """


MiddlewareEventType = TypeVar("MiddlewareEventType")

NextMiddlewareType = Callable[
    [MiddlewareEventType, dict[type[Any] | str, Any]], Awaitable[Any]
]

MiddlewareType: TypeAlias = (
    BaseMiddleware
    | Callable[
        [NextMiddlewareType[MiddlewareEventType], MiddlewareEventType, dict[str, Any]],
        Awaitable[Any],
    ]
)
