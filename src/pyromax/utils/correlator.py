import asyncio
from asyncio import Future
from typing import Any


class Correlator:
    def __init__(self):
        self._counter = 0
        self._counter_lock = asyncio.Lock()



    async def get_counter(self):
        async with self._counter_lock:
            return self._counter

    def counter_increment(self):
        self._counter += 1



    # def add_to_responses(self, response):
    #     self.__responses.append(response)

    # def push(self, request, response) -> bool:
    #     if request in self.__pending:
    #         future = self.__pending.pop(request)
    #         future.set_result(response)
    #         print(f'Response: {response}')
    #         return True
    #     return False


    # def pop(self, request) -> Future:
    #     future = asyncio.get_running_loop().create_future()
    #     if request in self.__responses:
    #         future.set_result(request)
    #         return future
    #     self.__pending[request] = future
    #     return future


    # def check_entry(self, entry) -> bool:
    #     if entry in self.__pending:
    #         return True
    #     return False