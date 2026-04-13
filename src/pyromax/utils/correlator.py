import asyncio


class Correlator:
    def __init__(self) -> None:
        self._counter = 0
        self._counter_lock = asyncio.Lock()



    async def get_counter(self) -> int:
        async with self._counter_lock:
            return self._counter

    def counter_increment(self) -> None:
        self._counter += 1
