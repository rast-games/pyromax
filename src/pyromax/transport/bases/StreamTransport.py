from abc import abstractmethod
from typing import Any

from .base import BaseTransport


class StreamTransport(BaseTransport):
    @abstractmethod
    async def send(self, request: Any) -> None:
        pass

    @abstractmethod
    async def recv(self) -> Any:
        pass


    @abstractmethod
    async def close(self) -> None:
        pass


    @abstractmethod
    async def connect(self) -> None:
        pass