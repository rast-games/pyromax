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
