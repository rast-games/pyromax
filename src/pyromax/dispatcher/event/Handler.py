from __future__ import annotations

from collections.abc import Callable, Awaitable, Iterable
from typing import Any, TYPE_CHECKING, Generic
from dataclasses import dataclass

from ..ObserverPattern import Observer
from ...utils import inspect_and_form

from .UpdateType import Update


from magic_filter import MagicFilter

if TYPE_CHECKING:
    from ...filters import Filter

@dataclass
class FilterObject:
    _filter: Filter | MagicFilter

    async def __call__(self, update: Update, data: dict[Any, Any]) -> Any:
        if isinstance(self._filter, MagicFilter):
            return self._filter.resolve(update)
        return await self._filter(update, data)

class Handler(Observer, Generic[Update]):
    """Wrap a callable handler with filters and a pattern."""
    def __init__(self, function: Callable[..., Any], filters: Iterable[Filter | MagicFilter], pattern: Callable[[Update], Any] | None = None):
        """Create a handler wrapper.

        Parameters
        ----------
        function
            Async callable to execute.
        filters
            Iterable of filters to apply before calling the handler.
        pattern
            Optional predicate used as a final condition.
        """
        self.function = function
        self.filters = [FilterObject(f) for f in filters]
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

