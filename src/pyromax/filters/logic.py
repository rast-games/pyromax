from abc import ABC
from collections.abc import Callable, Awaitable
from typing import Any

from ..models import BaseMaxObject
from .base import Filter


class _logicFilter(Filter, ABC):
    pass


class _invertFilter(_logicFilter):

    def __init__(self, target: Filter) -> None:
        super().__init__()
        self.target = target


    @property
    def callback(self) -> Callable[..., Awaitable[bool | dict[str, Any]]]:
        return self.target.callback

    @property
    def work_with(self) -> tuple[type[BaseMaxObject]]:
        return self.target.work_with

    async def _check(self, *args: Any, **kwargs: Any) -> bool:
        return not await self.target._check(*args, **kwargs)


    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self.target})'