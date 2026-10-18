from __future__ import annotations

from collections.abc import Callable, Iterable, Awaitable
from typing import Generic, TYPE_CHECKING, Any

from .base import SkipHandler
from ..ObserverPattern import Observer
from .Handler import Handler, FilterObject
from ..middlewares.manager import MiddlewareManager
from ..middlewares.base import MiddlewareType
from .UpdateType import ResolvedUpdate, MaxObject, UNHANDLED

if TYPE_CHECKING:
    from ...filters import Filter
    from ..Router import Router
    from ...filters.magic import MagicFilter


class StandardMaxEventObserver(Observer, Generic[ResolvedUpdate]):
    """Event observer that stores handlers for a specific update type.

    The observer dispatches incoming updates to registered handlers and
    stops propagation when one handler successfully processes the update.
    """

    def __init__(
        self, router: Router, event_name: str, type_of_update: type[ResolvedUpdate]
    ) -> None:
        """Create an event observer.

        :param router: Parent router that owns this observer.
        :type router: Router
        :param event_name: Name of the event.
        :type event_name: str
        :param type_of_update: Update type accepted by this observer.
        :type type_of_update: type[ResolvedUpdate]
        """
        self.type_of_update: type[ResolvedUpdate] = type_of_update
        self.router = router
        self.event_name: str = event_name
        self.handlers: list[Handler[ResolvedUpdate]] = []

        self.middleware = MiddlewareManager()
        self.outer_middleware = MiddlewareManager()

        # Re-used filters check method from already implemented handler object
        # with dummy callback which never will be used
        async def handler_dummy() -> bool:
            """Handler dummy.

            :returns: True when the requested condition is satisfied; otherwise False.
            :rtype: bool
            """
            return True

        self._handler: Handler[MaxObject] = Handler(
            pattern=lambda _: True, filters=[], function=handler_dummy
        )

    def register(
        self,
        callback: Callable[..., Awaitable[Any]],
        *filters: Filter | MagicFilter,
        pattern: Callable[[ResolvedUpdate], Any] | None = None,
        soft_propagate: bool = False,
    ) -> None:
        """Register a new handler with this observer.

        :param callback: Callback to invoke.
        :type callback: Callable[..., Awaitable[Any]]
        :param filters: Filter | MagicFilter instance to process.
        :type filters: Filter | MagicFilter
        :param pattern: Callable to invoke.
        :type pattern: Callable[[ResolvedUpdate], Any] | None
        """
        self.handlers.append(
            Handler(
                function=callback,
                filters=[FilterObject(filter_) for filter_ in filters],
                pattern=pattern,
                soft_propagate=soft_propagate,
            )
        )

    def filter(self, *filters: Filter | MagicFilter) -> None:
        """Register filter for all handlers of this event observer

        :param filters: positional filters

        :type filters: Filter | MagicFilter
        """
        if self._handler.filters is None:
            self._handler.filters = []
        self._handler.filters.extend([FilterObject(filter_) for filter_ in filters])

    def _resolve_middlewares(self) -> list[MiddlewareType[MaxObject]]:
        """Resolve middlewares.

        :returns: The resulting collection.
        :rtype: list[MiddlewareType[MaxObject]]
        """
        middlewares: list[MiddlewareType[MaxObject]] = []
        for router in reversed(tuple(self.router.chain_head)):
            observer = router.events.get(self.event_name)
            if observer:
                middlewares.extend(observer.middleware)

        return middlewares

    async def is_my_update(self, update: ResolvedUpdate) -> bool:
        """Check whether the update belongs to this observer.

        :param update: Incoming update to process.
        :type update: ResolvedUpdate
        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        """
        return type(update) is self.type_of_update

    def wrap_outer_middleware(
        self,
        callback: Any,
        event: MaxObject,
        data: dict[Any, Any],
    ) -> Any:
        """Wrap outer middleware.

        :param callback: Callback to invoke.
        :type callback: Any
        :param event: Incoming event to process.
        :type event: MaxObject
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any]
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        """
        wrapped_outer = self.middleware.wrap_middlewares(
            self.outer_middleware,
            callback,
        )
        return wrapped_outer(event, data)

    async def check_root_filters(self, event: MaxObject, data: dict[Any, Any]) -> Any:
        """Check root filters.

        :param event: Incoming event to process.
        :type event: MaxObject
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any]
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        """
        return await self._handler.check(event, data)

    async def update(
        self, update: ResolvedUpdate, data: dict[Any, Any] | None = None
    ) -> Any:
        """Pass an update through registered handlers.

        :param update: Incoming update to process.
        :type update: ResolvedUpdate
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any] | None
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        :raises ValueError: If data cannot be None.
        """
        if data is None:
            raise ValueError("data cannot be None")
        for handler in self.handlers:
            result, data_updated = await handler.check(update, data=data)
            if result:
                data_updated.update({Handler: handler})

                try:
                    wrapped_inner = MiddlewareManager.wrap_middlewares(
                        self._resolve_middlewares(), handler.update
                    )

                    return await wrapped_inner(update, data_updated)
                except SkipHandler:
                    continue
        return UNHANDLED

    def include_event(self, event: StandardMaxEventObserver[ResolvedUpdate]) -> None:
        """Merge handlers from another event observer.

        :param event: Incoming event to process.
        :type event: StandardMaxEventObserver[ResolvedUpdate]
        """
        self.handlers += event.handlers

    def include_events(
        self, events: Iterable[StandardMaxEventObserver[ResolvedUpdate]]
    ) -> None:
        """Merge handlers from multiple event observers.

        :param events: Collection of events.
        :type events: Iterable[StandardMaxEventObserver[ResolvedUpdate]]
        """
        for event in events:
            self.include_event(event)

    def __call__(
        self,
        *filters: Any,
        pattern: Callable[[ResolvedUpdate], Any] | None = None,
        soft_propagate: bool = False,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register a handler decorator for this observer.

        :param filters: The filters value.
        :type filters: Any
        :param pattern: Callable to invoke.
        :type pattern: Callable[[ResolvedUpdate], Any] | None
        :returns: The resulting Callable[[Callable[..., Any]], None] value.
        :rtype: Callable[[Callable[..., Any]], None]
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            """Decorator.

            :param func: Callable to invoke.
            :type func: Callable[..., Any]
            """
            self.register(
                func,
                *filters,
                pattern=pattern,
                soft_propagate=soft_propagate,
            )
            return func

        return decorator
