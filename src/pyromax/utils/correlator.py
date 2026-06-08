import asyncio


class Correlator:
    def __init__(self) -> None:
        self._counter = 0
        self._counter_lock = asyncio.Lock()


    async def next_counter(self) -> int:
        async with self._counter_lock:
            counter = self._counter
            self._counter += 1
            return counter