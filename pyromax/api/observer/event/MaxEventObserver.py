from typing import TYPE_CHECKING, Union
import inspect


from pyromax.exceptions import AnnotationHandlerError
from pyromax.api.observer import ObserverPattern

from pyromax.api.observer import Handler
from pyromax.api.observer import Router

if TYPE_CHECKING:
    from pyromax.filters import Filter
    from pyromax.api import MaxApi
    from pyromax.types import Update

class MaxEventObserver(ObserverPattern.Observer):
    """
        Event observer for Max events

        Here you can register handler with filter.
        This observer will stop event propagation when first handler is pass.
        """

    def __init__(self, router: 'Router', event_name: str, opcode: int, type_of_update) -> None:
        self.type_of_update = type_of_update
        self.opcode = opcode
        self.router: Router = router
        self.event_name: str = event_name
        self.handlers: list['Handler'] = []

        # self.middleware = MiddlewareManager()
        # self.outer_middleware = MiddlewareManager()

        # Re-used filters check method from already implemented handler object
        # with dummy callback which never will be used
        # self._handler = Handler(pattern=lambda: True, filters=[])

    async def update(self, update, max_api: 'MaxApi', data: dict = None) -> tuple['Handler',  dict] | tuple[bool, dict]:
        if data is None:
            raise ValueError('data cannot be None')
        for handler in self.handlers:
            if await handler.update(update, max_api, data=data):
                return handler, data
        return False, data


    def include_event(self, event: 'MaxEventObserver'):
        self.handlers += event.handlers


    def include_events(self, events):
        for event in events:
            self.include_event(event)


    def __call__(self, *filters: 'Filter', pattern=None, from_me: bool = False):
        def decorator(func):
            signature = inspect.signature(func)
            args = [param.annotation for param in signature.parameters.values()]
            if inspect._empty in args:
                raise AnnotationHandlerError('Need annotation all params in handler')
            handler = Handler(func, filters=filters, pattern=pattern, args=args, from_me=from_me)
            self.handlers.append(handler)
        return decorator


