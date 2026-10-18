from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Awaitable


from ..utils import inspect_and_form

if TYPE_CHECKING:
    from ..models import BaseMaxObject
    from ..dispatcher.event import ResolvedUpdate


class Filter(ABC):
    """Base class for user-defined and built-in filters.

    Subclasses must implement the asynchronous _check method and
    define which update types they accept through work_with.
    """

    def __init__(self) -> None:
        """Initialize the filter.
        """
        self._logger = logging.getLogger(f"{self.__class__.__name__}")

    _SKIP_CHECK_PREPARATIONS: bool = False

    # if TYPE_CHECKING:
    #     # This checking type-hint is needed because mypy checks validity of overrides and raises:
    #     # error: Signature of "__call__" incompatible with supertype "BaseFilter"  [override]
    #     # https://mypy.readthedocs.io/en/latest/error_code_list.html#check-validity-of-overrides-override
    #     __call__: Callable[Update, Awaitable[bool | dict[str, Any]]]
    # else:  # pragma: no cover

    async def __call__(
        self, update: ResolvedUpdate, data: dict[Any, Any], *args: Any, **kwargs: Any
    ) -> bool | dict[str, Any]:
        """Return whether the event matches the  filter.

        :param update: Incoming update to process.
        :type update: ResolvedUpdate
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any]
        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting bool | dict[str, Any] value.
        :rtype: bool | dict[str, Any]
        """
        if self._SKIP_CHECK_PREPARATIONS:
            return await self._check(update, data, *args, **kwargs)

        if type(update) not in self.work_with:
            return False

        data.update({type(elem): elem for elem in args})

        data.update(kwargs)

        check_args = inspect_and_form(self.callback, data=data)

        return await self._check(**check_args)

    def __invert__(self) -> Filter:
        """Invert.

        :returns: The resulting Filter value.
        :rtype: Filter
        """
        from .logic import invert_f

        return invert_f(self)

    @property
    @abstractmethod
    def work_with(self) -> tuple[type[BaseMaxObject], ...]:
        """Work with.

        :returns: The resulting tuple[type[BaseMaxObject], ...] value.
        :rtype: tuple[type[BaseMaxObject], ...]
        """
        pass

    @property
    def callback(
        self, *args: Any, **kwargs: Any
    ) -> Callable[..., Awaitable[bool | dict[str, Any]]]:
        """Callback.

        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting Callable[..., Awaitable[bool | dict[str, Any]]] value.
        :rtype: Callable[..., Awaitable[bool | dict[str, Any]]]
        """
        return self._check

    @abstractmethod
    async def _check(self, *args: Any, **kwargs: Any) -> bool | dict[Any, Any]:
        """This method should be overridden.

        Accepts incoming event and should return boolean or dict.

        :return: :class:`bool` or :class:`dict[str, Any]`

        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting bool | dict[Any, Any] value.
        :rtype: bool | dict[Any, Any]
        """
        pass
