from __future__ import annotations

from collections.abc import Callable, Awaitable, Iterable
from typing import Any, TYPE_CHECKING, Generic

from ..ObserverPattern import Observer
from ...utils import inspect_and_form

from .UpdateType import Update

if TYPE_CHECKING:
    from ...filters import Filter


class Handler(Observer, Generic[Update]):
    def __init__(self, function: Callable[..., Any], filters: Iterable[Filter], pattern: Callable[[Update], Any] | None = None):
        self.function = function
        self.filters = filters
        self.pattern = pattern
        self.function = function
        self.pattern = pattern


    async def _propagate_update(self, update: Update, data: dict[Any, Any]) -> bool:
        if self.pattern is None and not self.filters:
            return True

        for f in self.filters:

            check = await f(update, data=data)
            if isinstance(check, dict):
                data.update(check)
            if not check:
                return False

        if self.pattern is not None:
            return bool(self.pattern(update))
        return True


    async def update(self, update: Update, data: dict[Any, Any] | None = None) -> bool:
        if data is None:
            raise ValueError('data cannot be None')
        check = await self._propagate_update(update, data)
        if check:
            args = inspect_and_form(self.function, data)
            await self.function(**args)
            return True
        return False


    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} filters={self.filters}> pattern={self.pattern}>>'

