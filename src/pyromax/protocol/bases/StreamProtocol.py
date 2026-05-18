from abc import abstractmethod
from collections.abc import Callable
from typing import Any, Generic

from .base import BaseMaxProtocol, T, R
from ...transport import StreamTransport


class StreamMaxProtocol(BaseMaxProtocol[T, R], Generic[T, R]):

    @abstractmethod
    async def connect(self, gen: int) -> None: pass


    @abstractmethod
    async def close(self) -> None: pass


    @property
    @abstractmethod
    def transport(self) -> StreamTransport: pass

