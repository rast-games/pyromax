from __future__ import annotations

from collections.abc import Callable, Iterable, Awaitable
from typing import TypeVar, Generic, TYPE_CHECKING, Any

from .base import SkipHandler
from ..ObserverPattern import Observer
from .Handler import Handler, FilterObject
from ..middlewares.manager import MiddlewareManager
from ..middlewares.base import MiddlewareType
from ...models import BaseMaxObject
from ...protocol import Response
from .UpdateType import Update, MaxObject, UNHANDLED

if TYPE_CHECKING:
    from ...filters import Filter
    from ..Router import Router
    from ...filters.magic import MagicFilter





class StandardMaxEventObserver(Observer, Generic[Update]):
    """Event observer that stores handlers for a specific update type.

    The observer dispatches incoming updates to registered handlers and
    stops propagation when one handler successfully processes the update.
    """

    def __init__(self, router: Router, event_name: str, type_of_update: type[Update]) -> None:
        """Create an event observer.

        Parameters
        ----------
        router
            Parent router that owns this observer.
        event_name
            Name of the event.
        type_of_update
            Update type accepted by this observer.
        """
        self.type_of_update: type[Update] = type_of_update
        self.router = router
        self.event_name: str = event_name
        self.handlers: list[Handler[Update]] = []

        self.middleware = MiddlewareManager()
        self.outer_middleware = MiddlewareManager()

        # Re-used filters check method from already implemented handler object
        # with dummy callback which never will be used
        async def handler_dummy() -> bool:
            return True
        self._handler: Handler = Handler(pattern=lambda _: True, filters=[], function=handler_dummy)

    def register(self, callback: Callable[..., Awaitable[Any]], *filters: Filter | MagicFilter, pattern: Callable[[Update], Any] | None = None) -> None:
        """Register a new handler with this observer."""
        self.handlers.append(
            Handler(
                function=callback,
                filters=[FilterObject(filter_) for filter_ in filters],
                pattern=pattern
            )
        )

    def filter(self, *filters: Filter | MagicFilter) -> None:
        """
        Register filter for all handlers of this event observer

        :param filters: positional filters
        """
        if self._handler.filters is None:
            self._handler.filters = []
        self._handler.filters.extend([FilterObject(filter_) for filter_ in filters])



    def _resolve_middlewares(self) -> list[MiddlewareType[MaxObject]]:
        middlewares: list[MiddlewareType[MaxObject]] = []
        for router in reversed(tuple(self.router.chain_head)):
            observer = router.events.get(self.event_name)
            if observer:
                middlewares.extend(observer.middleware)

        return middlewares

    async def is_my_update(
            self,
            update: Update
    ) -> bool:
        """Check whether the update belongs to this observer."""
        return type(update) is self.type_of_update


    def wrap_outer_middleware(
        self,
        callback: Any,
        event: MaxObject,
        data: dict[Any, Any],
    ) -> Any:
        wrapped_outer = self.middleware.wrap_middlewares(
            self.outer_middleware,
            callback,
        )
        return wrapped_outer(event, data)


    async def check_root_filters(self, event: MaxObject, data: dict[Any, Any]) -> Any:
        return await self._handler.check(event, data)


    async def update(self, update: Update, data: dict[Any, Any] | None = None) -> Any:
        """Pass an update through registered handlers."""
        if data is None:
            raise ValueError('data cannot be None')
        for handler in self.handlers:
            if await handler.check(update, data=data):
                data.update(
                    {
                        Handler: handler
                    }
                )

                try:
                    wrapped_inner = MiddlewareManager.wrap_middlewares(
                        self._resolve_middlewares(),
                        handler.update
                    )

                    return await wrapped_inner(update, data)
                except SkipHandler:
                    continue
        return UNHANDLED


    def include_event(self, event: StandardMaxEventObserver[Update]) -> None:
        """Merge handlers from another event observer."""
        self.handlers += event.handlers


    def include_events(self, events: Iterable[StandardMaxEventObserver[Update]]) -> None:
        """Merge handlers from multiple event observers."""
        for event in events:
            self.include_event(event)


    def __call__(self, *filters: Any, pattern: Callable[[Update], Any] | None = None)\
            -> Callable[[Callable[..., Any]], None]:
        """Register a handler decorator for this observer."""
        def decorator(func: Callable[..., Any]) -> None:
            self.register(func, *filters, pattern=pattern)
        return decorator


