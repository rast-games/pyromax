from typing import Coroutine

def return_self_after_method(initializer):
    """
    Need use to async initializer in __new__ method
    Args:
          initializer (function): method that will be called, your async initializer
    Returns:
          result of init or self object if initializer returns None

    Examples:
        class ExampleClass1:
            async def your_async_init(self):
                self.test = 'test'

            def __new__(cls, *args, **kwargs):
                self = object.__new__(cls)
                init = return_self_after_method(self.your_async_init)
                return init(self, *args, **kwargs)

            def __repr__(self):
                return 'ExampleClass1'

        class ExampleClass2:
            async def your_async_init(self):
                self.test = 'test'
                return 'init_return_another'

            def __new__(cls, *args, **kwargs):
                self = object.__new__(cls)
                init = return_self_after_method(self.your_async_init)
                return init(self, *args, **kwargs)


        async def main():
             example1 = await ExampleClass1()
             example2 = await ExampleClass2()
             print(example1) # -> 'ExampleClass1'
             print(example2) # -> 'init_return_another'

        if __name__ == '__main__':
            asyncio.run(main())

        Result:
            ExampleClass1
            init_return_another
    """
    async def initializer_wrapper(self, *args, **kwargs) -> Coroutine:
        result = await initializer(self, *args, **kwargs)
        # if result is None:
        #     print('self returned')
        #     return self
        # print('return result')
        # return result
        return result or self
    return initializer_wrapper