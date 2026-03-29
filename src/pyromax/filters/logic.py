from abc import ABC

from src.pyromax import BaseMaxObject
from src.pyromax.filters import Filter


class _logicFilter(Filter, ABC):
    pass


class _invertFilter(_logicFilter):

    def __init__(self, target: Filter):
        self.target = target


    @property
    def callback(self):
        return self.target.callback

    @property
    def work_with(self) -> type[BaseMaxObject]:
        return self.target.work_with

    async def _check(self, *args, **kwargs) -> bool:
        return not await self.target._check(*args, **kwargs)


    def __repr__(self):
        return f'{self.__class__.__name__}({self.target})'