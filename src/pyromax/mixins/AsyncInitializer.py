from __future__ import annotations
import asyncio
from collections.abc import Awaitable, Generator
from typing import TypeVar, Any, Generic

from typing_extensions import Self

from ..utils import return_self_after_method

import abc


# T = TypeVar('T', bound=Any)




class AsyncInitializerMixin(abc.ABC):
    """
    Added async initializer in class, for begin you need inherit from AsyncInitializerMixin and create a method with
    _async_init name.
    You can nothing return in _async_init, and in default it be return self
    or
    You can return anything except None
    Coroutines can be awaited in this init(in example: await asyncio.sleep(1))

    in subclasses you cannot overwrite __await__ method, else it crack static analyses.
    If you need use __await__, use a async factory method

    Example:
        class NeedAsyncInit(AsyncInitializerMixin):
            async def _init(self):
                await asyncio.sleep(1)
                self.test = 'test'

            def __repr__(self):
                return 'NeedAsyncInit'

        class AnotherNeedAsyncInit(AsyncInitializerMixin):
            async def _init(self):
                await asyncio.sleep(1)
                self.test = 'test'
                return 'another return'

        async def main():
            example1 = NeedAsyncInit()
            example2 = AnotherNeedAsyncInit()
            print(example1)
            print(example2)


        if __name__ == '__main__':
            asyncio.run(main())

        CONSOLE:
            NeedAsyncInit
            another return
    """

    def __new__(cls: type[Self], *args: Any, **kwargs: Any) -> Awaitable[Self]: # type: ignore[misc]
        __instance = object.__new__(cls)
        __init = return_self_after_method(cls._async_init)
        return __init(__instance, *args, **kwargs)


    def __await__(self: Self) -> Generator[Any, Any, Self]:
        """just blank"""
        if False: yield
        return self

    @abc.abstractmethod
    async def _async_init(self, *args: Any, **kwargs: Any) -> Any:
        ...


# class NeedAsyncInit(AsyncInitializerMixin['NeedAsyncInit']):
#
#     async def _async_init(self):
#         print('_async_init()')
#         await asyncio.sleep(1)
#         self.test_field = 'test_field'
#
# async def main():
#     example = await NeedAsyncInit()
#     print(example.test_field)
#
# if __name__ == '__main__':
#     asyncio.run(main())