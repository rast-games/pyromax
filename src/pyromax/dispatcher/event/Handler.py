from __future__ import annotations

from collections.abc import Callable
from typing import Any, TYPE_CHECKING, Generic, Optional, TypeVar, Mapping, cast
from dataclasses import dataclass
import logging
import inspect


from ..ObserverPattern import Observer
from ...utils import inspect_and_form
from ...filters.magic import MagicFilter

from .UpdateType import ResolvedUpdate, MaxObject
from ...filters import Filter


from magic_filter.magic import MagicFilter as OriginalMagicFilter

if TYPE_CHECKING:
    pass


f = TypeVar("f", bound=Filter | Callable[[MaxObject, Mapping[Any, Any]], Any])


@dataclass
class FilterObject(Generic[f]):
    filter: f
    magic: Optional[OriginalMagicFilter | MagicFilter] = None

    def __post_init__(self) -> None:
        """Post init."""
        self.resolve = self._resolve
        self.awaitable = inspect.isawaitable(
            self.filter
        ) or inspect.iscoroutinefunction(self.filter)
        if isinstance(self.filter, OriginalMagicFilter):
            self.magic = self.filter
            self.resolve = self._magic_resolve

            if not isinstance(self.magic, MagicFilter):
                logging.getLogger("Magic Filter").info(
                    msg="You are using F provided by magic_filter package directly, "
                    "but it lacks `_SKIP_CHECK_PREPARATIONS: bool = True` and \n"
                    " `async def _check(self, update, *args: Any, **kwargs: Any) -> bool: return self.resolve(update)` extension."
                    "\n Please change the import statement: from `from magic_filter import F` "
                    "to `from pyromax import F` to silence this warning.",
                    stacklevel=6,
                )
        if isinstance(self.filter, Filter):
            self.awaitable = True

    async def _magic_resolve(self, update: ResolvedUpdate, data: dict[Any, Any]) -> Any:
        """Magic resolve.

        :param update: Incoming update to process.
        :type update: ResolvedUpdate
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any]
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        """
        self.magic: MagicFilter
        return self.magic.resolve(update)

    async def _resolve(
        self, update: ResolvedUpdate, data: dict[Any, Any]
    ) -> bool | dict[str, Any]:
        """Resolve.

        :param update: Incoming update to process.
        :type update: ResolvedUpdate
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any]
        :returns: The resulting bool | dict[str, Any] value.
        :rtype: bool | dict[str, Any]
        """
        assert not isinstance(self.filter, MagicFilter)
        if self.awaitable:
            return await self.filter(update, data)
        return cast(bool | dict[str, Any], self.filter(update, data))

    async def __call__(
        self, update: ResolvedUpdate, data: dict[Any, Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Invoke the filter object.

        :param update: Incoming update to process.
        :type update: ResolvedUpdate
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any]
        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        """
        return await self.resolve(update, data)


class Handler(Observer, Generic[ResolvedUpdate]):
    """Wrap a callable handler with filters and a pattern."""

    def __init__(
        self,
        function: Callable[..., Any],
        filters: list[FilterObject[Any]],
        pattern: Callable[[ResolvedUpdate], Any] | None = None,
        soft_propagate: bool = False,
    ):
        """Create a handler wrapper.

        :param function: Async callable to execute.
        :type function: Callable[..., Any]
        :param filters: Iterable of filters to apply before calling the handler.
        :type filters: list[FilterObject[Any]]
        :param pattern: Optional predicate used as a final condition.
        :type pattern: Callable[[ResolvedUpdate], Any] | None
        """
        self.function = function
        self.filters = filters
        self.pattern = pattern
        self.function = function
        self._soft_propagate = soft_propagate

    async def _propagate_update(
        self, update: ResolvedUpdate, data: dict[Any, Any]
    ) -> tuple[bool, dict[Any, Any]]:
        data_copy = data.copy()
        """Propagate update.

        :param update: Incoming update to process.
        :type update: ResolvedUpdate
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any]
        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        """
        if self.pattern is None and not self.filters:
            return True, data_copy
        for f in self.filters:
            check = await f(update, data=data_copy)
            if isinstance(check, dict):
                data_copy.update(check)
            if not check:
                return False, data_copy
        if self.pattern is not None:
            return bool(self.pattern(update)), data_copy
        return True, data_copy

    async def check(
        self, update: ResolvedUpdate, data: dict[Any, Any]
    ) -> tuple[bool, dict[Any, Any]]:
        """Check.

        :param update: Incoming update to process.
        :type update: ResolvedUpdate
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any]
        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        """
        return await self._propagate_update(update, data)

    async def update(
        self, update: ResolvedUpdate, data: dict[Any, Any] | None = None
    ) -> Any:
        """Update.

        :param update: Incoming update to process.
        :type update: ResolvedUpdate
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any] | None
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        :raises ValueError: If data cannot be None.
        """
        if data is None:
            raise ValueError("data cannot be None")
        # check = await self._propagate_update(update, data)
        # if check:
        args = inspect_and_form(
            self.function,
            data,
            strict=not self._soft_propagate,
        )
        return await self.function(**args)
        # return UNHANDLED

    def __repr__(self) -> str:
        """Return the developer representation of the handler.

        :returns: The resulting str value.
        :rtype: str
        """
        return f"<{self.__class__.__name__} filters={self.filters}> pattern={self.pattern}>>"
