from __future__ import annotations

from collections.abc import Callable, Awaitable, Iterable, Coroutine
from typing import Any, TYPE_CHECKING, Generic, Union, Optional
from dataclasses import dataclass
import logging


from ..ObserverPattern import Observer
from ...utils import inspect_and_form
from ...filters.magic import MagicFilter

from .UpdateType import Update


from magic_filter.magic import MagicFilter as OriginalMagicFilter

if TYPE_CHECKING:
    from ...filters import Filter
    from ...models import BaseMaxObject

CallbackType = Callable[..., Any]

@dataclass
class FilterObject:
    filter: Filter | MagicFilter
    magic: Optional[OriginalMagicFilter | MagicFilter] = None

    def __post_init__(self):
        self.resolve = self._resolve
        if isinstance(self.filter, OriginalMagicFilter):
            self.magic = self.filter
            self.resolve = self._magic_resolve

            if not isinstance(self.magic, MagicFilter):
                logging.getLogger('Magic Filter').info(
                    msg="You are using F provided by magic_filter package directly, "
                    "but it lacks `_SKIP_CHECK_PREPARATIONS: bool = True` and \n"
                    " `async def _check(self, update, *args: Any, **kwargs: Any) -> bool: return self.resolve(update)` extension."
                    "\n Please change the import statement: from `from magic_filter import F` "
                    "to `from pyromax import F` to silence this warning.",
                    stacklevel=6
                )


    async def _magic_resolve(self, update, *args) -> Any:
        self.magic: MagicFilter
        return self.magic.resolve(update)


    async def _resolve(self, update, data) -> bool | dict[str, Any]:
        # from ...filters import Filter
        assert not isinstance(self.filter, MagicFilter)
        return await self.filter(update, data)


    async def __call__(self, update: Update, data: dict[Any, Any], *args, **kwargs) -> Any:
        return await self.resolve(update, data)

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

