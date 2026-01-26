from typing import Coroutine

from pyromax.utils.return_self import return_self_after_method

import abc


class AsyncInitializerMixin(abc.ABC):
    """
    Added async initializer in class, for begin you need inherit from AsyncInitializerMixin and create a method with
    _init name.
    You can nothing return in _init, and in default it be return self
    or
    You can return anything except None
    Coroutines can be awaited in this init(in example: await asyncio.sleep(1))
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

    def __new__(cls, *args, **kwargs) -> Coroutine:
        self = object.__new__(cls)
        init = return_self_after_method(cls._init)
        return init(self, *args, **kwargs)

    def __await__(self):
        """just blank"""
        ...
        return self

    @abc.abstractmethod
    async def _init(self, *args, **kwargs):
        ...