from __future__ import annotations
from typing import TypeVar, Generic, TYPE_CHECKING

from ..ObserverPattern import Observer
from .Handler import Handler
from src.pyromax.dispatcher import Router
from src.pyromax.models import BaseMaxObject
from src.pyromax.protocol import Response

if TYPE_CHECKING:
    from src.pyromax.filters import Filter


Update = TypeVar('Update', BaseMaxObject, Response)


class StandardMaxEventObserver(Observer, Generic[Update]):
    """
        Event observer for Max events

        Here you can register handler with filter.
        This observer will stop event propagation when first handler is pass.
        """

    def __init__(self, router: Router, event_name: str, type_of_update: type[Update]) -> None:
        self.type_of_update = type_of_update
        self.router: Router = router
        self.event_name: str = event_name
        self.handlers: list['Handler'] = []

        # self.middleware = MiddlewareManager()
        # self.outer_middleware = MiddlewareManager()

        # Re-used filters check method from already implemented handler object
        # with dummy callback which never will be used
        # self._handler = Handler(pattern=lambda: True, filters=[])


    def is_my_update(
            self,
            update: BaseMaxObject | Response
    ) -> bool:
        return type(update) is self.type_of_update

    async def update(self, update: Update, data: dict = None) -> bool:
        if data is None:
            raise ValueError('data cannot be None')
        for handler in self.handlers:
            if await handler.update(update, data=data):
                return True
        return False


    def include_event(self, event: StandardMaxEventObserver):
        self.handlers += event.handlers


    def include_events(self, events):
        for event in events:
            self.include_event(event)


    def __call__(self, *filters: Filter, pattern=None):
        def decorator(func):
            handler = Handler(func, filters=filters, pattern=pattern)
            self.handlers.append(handler)
        return decorator


