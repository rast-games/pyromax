from __future__ import annotations
from collections.abc import Awaitable
from abc import ABCMeta, abstractmethod, ABC
from typing import TypeVar, Any, Protocol, cast


from ..utils import return_self_after_method


class AsyncConstructorABC(ABC):
    @abstractmethod
    async def _async_init(self, *args: Any, **kwargs: Any) -> Any: pass


T = TypeVar('T', bound=AsyncConstructorABC)


class NewMethod(Protocol[T]):
    def __call__(
        self,
        cls: type[T],
        *args: Any,
        **kwargs: Any,
    ) -> T: ...


class AsyncConstructorMeta(ABCMeta):
    @staticmethod
    async def _call_wrapper(cls: type[T], *args: Any, **kwargs: Any) -> T:
        if cls.__new__ == object.__new__:
            __instance = cls.__new__(cls)
        else:
            __instance = cast(NewMethod[T], cls.__new__)(cls, *args, **kwargs)
        __init = return_self_after_method(cls._async_init)
        return await __init(__instance, *args, **kwargs)


    # mypy doesn't support generic __call__ on metaclasses
    def __call__(cls: type[T], *args: Any, **kwargs: Any) -> Awaitable[T]: # type: ignore[misc]
        return AsyncConstructorMeta._call_wrapper(cls, *args, **kwargs)


class AsyncInitializerMixin(AsyncConstructorABC, metaclass=AsyncConstructorMeta):
    """
    Added async initializer in class, for begin you need inherit from AsyncInitializerMixin and create a method with
    _async_init name.
    You can nothing return in _async_init, and in default it be return self
    or
    You can return anything except None
    Coroutines can be awaited in this init(in example: await asyncio.sleep(1))


    Example:
        class NeedAsyncInit(AsyncInitializerMixin):
            async def _async_init(self):
                await asyncio.sleep(1)
                self.test = 'test'

            def __repr__(self):
                return 'NeedAsyncInit'

        class AnotherNeedAsyncInit(AsyncInitializerMixin):
            async def _async_init(self):
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

T_co = TypeVar('T_co', covariant=True)

class AsyncConstructorType(Protocol[T_co]):
    def __call__(self, *args: Any, **kwargs: Any) -> Awaitable[T_co]:
        ...