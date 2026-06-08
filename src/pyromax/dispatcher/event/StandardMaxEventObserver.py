from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TypeVar, Generic, TYPE_CHECKING, Any

from ..ObserverPattern import Observer
from .Handler import Handler
from ...models import BaseMaxObject
from ...protocol import Response
from .UpdateType import Update

if TYPE_CHECKING:
    from ...filters import Filter
    from ..Router import Router





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
        self.type_of_update = type_of_update
        self.router = router
        self.event_name: str = event_name
        self.handlers: list[Handler[Update]] = []

        # self.middleware = MiddlewareManager()
        # self.outer_middleware = MiddlewareManager()

        # Re-used filters check method from already implemented handler object
        # with dummy callback which never will be used
        # self._handler = Handler(pattern=lambda: True, filters=[])


    async def is_my_update(
            self,
            update: Update
    ) -> bool:
        """Check whether the update belongs to this observer."""
        return type(update) is self.type_of_update

    async def update(self, update: Update, data: dict[Any, Any] | None = None) -> bool:
        """Pass an update through registered handlers."""
        if data is None:
            raise ValueError('data cannot be None')
        for handler in self.handlers:
            if await handler.update(update, data=data):
                return True
        return False


    def include_event(self, event: StandardMaxEventObserver[Update]) -> None:
        """Merge handlers from another event observer."""
        self.handlers += event.handlers


    def include_events(self, events: Iterable[StandardMaxEventObserver[Update]]) -> None:
        """Merge handlers from multiple event observers."""
        for event in events:
            self.include_event(event)


    def __call__(self, *filters: Filter, pattern: Callable[[Update], Any] | None = None)\
            -> Callable[[Callable[..., Any]], None]:
        """Register a handler decorator for this observer."""
        def decorator(func: Callable[..., Any]) -> None:
            handler = Handler(func, filters=filters, pattern=pattern)
            self.handlers.append(handler)
        return decorator


