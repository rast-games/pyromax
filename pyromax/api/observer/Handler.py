from typing import List, Any, TYPE_CHECKING, Awaitable, Callable

from .ObserverPattern import Observer

if TYPE_CHECKING:
    from pyromax.api import MaxApi
    from pyromax.types import Update


class Handler(Observer):
    def __init__(self, function, pattern = lambda update: True, args: List[Any] = None, from_me=False, filters=[]):
        if args is None:
            args = []
        self.function = function
        self.pattern = pattern
        self.args = args
        self.function: Callable[[Any], Awaitable] = function
        self.pattern = pattern
        self.from_me = from_me


    async def update(self, update, max_api: 'MaxApi') -> bool:
        if update.has_sender_info and (update.sender == max_api.id) != self.from_me:
            return False
        return self.pattern(update)
