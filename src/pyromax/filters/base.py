from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from src.pyromax.dispatcher.event import Update
from src.pyromax.utils import inspect_and_form
if TYPE_CHECKING:
    from src.pyromax import BaseMaxObject


class Filter(ABC):
    """
    If you want to register own filters like builtin filters you will need to write subclass
    of this class with overriding the :code:`__call__`
    method and adding filter attributes.
    """

    def __init__(self):
        self._logger = logging.getLogger(f'{self.__class__.__name__}')


    # if TYPE_CHECKING:
    #     # This checking type-hint is needed because mypy checks validity of overrides and raises:
    #     # error: Signature of "__call__" incompatible with supertype "BaseFilter"  [override]
    #     # https://mypy.readthedocs.io/en/latest/error_code_list.html#check-validity-of-overrides-override
    #     __call__: Callable[Update, Awaitable[bool | dict[str, Any]]]
    # else:  # pragma: no cover

    async def __call__(self, update: Update, data, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:

        if not self.work_with == type(update):
            return False

        kwargs.update(
            {
                type(elem): elem
                for
                elem
                in
                args
            }
        )

        data.update(kwargs)

        check_args = inspect_and_form(self.callback, data=data)

        return await self._check(**check_args)

    def __invert__(self) -> Filter:
        from .logic import _invertFilter
        return _invertFilter(self)

    @property
    @abstractmethod
    def work_with(self) -> type[BaseMaxObject]: pass


    @property
    def callback(self):
        return self._check


    @abstractmethod
    async def _check(self, *args: Any, **kwargs: Any) -> bool | dict[str, Any]:
        """
        This method should be overridden.

        Accepts incoming event and should return boolean or dict.

        :return: :class:`bool` or :class:`dict[str, Any]`
        """
        pass