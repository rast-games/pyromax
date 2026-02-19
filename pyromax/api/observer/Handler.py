from collections.abc import Sequence
from typing import List, Any, TYPE_CHECKING, Awaitable, Callable

from .ObserverPattern import Observer

if TYPE_CHECKING:
    from pyromax.filters import Filter
    from pyromax.api import MaxApi
    from pyromax.types import Update


class Handler(Observer):
    def __init__(self, function, filters: Sequence['Filter'], pattern: None | Callable = None, args: List[Any] = None, from_me=False):
        if args is None:
            args = []
        self.function = function
        self.filters = filters
        self.pattern: Callable[[Any], bool] = pattern
        self.args = args
        self.function: Callable[[Any], Awaitable] = function
        self.pattern = pattern
        self.from_me = from_me


    async def update(self, update, max_api: 'MaxApi', data: dict = None) -> bool:
        if not self.pattern and not self.filters:
            return True
        if update.has_sender_info and (update.sender == max_api.id) != self.from_me:
            return False
        for f in self.filters:
            check = await f(update, max_api=max_api)
            if check:
                if data is not None:
                    data.update({
                        type(check): check
                    })
                return True
        if self.pattern:
            return self.pattern(update)
        return False

    def __repr__(self):
        return f'<{self.__class__.__name__} filters={self.filters}> pattern={self.pattern}> from_me={self.from_me}> args={self.args}>'

