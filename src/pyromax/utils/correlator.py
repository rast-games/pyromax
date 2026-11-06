import asyncio
import math

from ..exceptions import SequenceExhaustedError


class Correlator:
    def __init__(self, reset_lim: int | float = 65_535) -> None:
        if reset_lim <= 0:
            raise ValueError("reset_lim must be > 0")

        if isinstance(reset_lim, float):
            if math.isnan(reset_lim):
                raise ValueError("reset_lim must not be NaN")
            if not reset_lim.is_integer() and reset_lim != math.inf:
                raise ValueError("reset_lim must be an integer or infinity")

        self._counter = 0
        self._reset_lim = reset_lim
        self._counter_lock = asyncio.Lock()

    async def next_counter(self) -> int:
        async with self._counter_lock:
            if self._counter > self._reset_lim:
                raise SequenceExhaustedError("Sequence number range exhausted")

            counter = self._counter
            self._counter += 1

            return counter
