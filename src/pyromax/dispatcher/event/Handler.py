from __future__ import annotations
from typing import Any, TYPE_CHECKING, Awaitable, Callable, Iterable

from ..ObserverPattern import Observer
from ...utils import inspect_and_form

if TYPE_CHECKING:
    from ...filters import Filter
    from .StandardMaxEventObserver import Update

class Handler(Observer):
    def __init__(self, function, filters: Iterable[Filter], pattern: None | Callable = None):
        self.function = function
        self.filters = filters
        self.pattern: Callable[[Any], bool] = pattern
        self.function: Callable[[Any], Awaitable] = function
        self.pattern = pattern


    async def _propagate_update(self, update: Update, data: dict = None) -> bool:
        if not self.pattern and not self.filters:
            return True

        for f in self.filters:

            check = await f(update, data=data)
            if not check:
                return False

        if self.pattern:
            return self.pattern(update)
        return True


    async def update(self, update: Update, data: dict = None) -> bool:
        check = await self._propagate_update(update, data)
        if check:
            args = inspect_and_form(self.function, data)
            await self.function(**args)
            return True
        return False


    def __repr__(self):
        return f'<{self.__class__.__name__} filters={self.filters}> pattern={self.pattern}>>'

