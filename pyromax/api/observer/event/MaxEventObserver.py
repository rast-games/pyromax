from typing import TYPE_CHECKING, Union
import inspect


from pyromax.exceptions import AnnotationHandlerError
from pyromax.api.observer import ObserverPattern

from pyromax.api.observer import Handler

if TYPE_CHECKING:
    from pyromax.api.observer import Router
    from pyromax.api import MaxApi
    from pyromax.types import Update

class MaxEventObserver(ObserverPattern.Observer):
    """
        Event observer for Max events

        Here you can register handler with filter.
        This observer will stop event propagation when first handler is pass.
        """

    def __init__(self, router: 'Router', event_name: str, opcode: int) -> None:
        self.opcode = opcode
        self.router: Router = router
        self.event_name: str = event_name
        self.handlers: list['Handler'] = []

        # self.middleware = MiddlewareManager()
        # self.outer_middleware = MiddlewareManager()

        # Re-used filters check method from already implemented handler object
        # with dummy callback which never will be used
        # self._handler = Handler(pattern=lambda: True, filters=[])

    async def update(self, update: 'Update', max_api: 'MaxApi') -> Union['Handler',  bool]:

        for handler in self.handlers:
            if await handler.update(update, max_api):
                return handler
        return False

    def include_event(self, event: 'MaxEventObserver'):
        self.handlers += event.handlers


    def include_events(self, events):
        for event in events:
            self.include_event(event)


    def __call__(self, pattern=lambda update: True, from_me: bool = False):
        def decorator(func):
            signature = inspect.signature(func)
            args = [param.annotation for param in signature.parameters.values()]
            if inspect._empty in args:
                raise AnnotationHandlerError('Need annotation all params in handler')
            self.handlers.append(Handler(func, pattern, args, from_me=from_me))
        return decorator


