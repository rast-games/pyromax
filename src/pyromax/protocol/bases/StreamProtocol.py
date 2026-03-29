from abc import abstractmethod, abstractproperty
from typing import Any


from .base import BaseMaxProtocol


class StreamMaxProtocol(BaseMaxProtocol):

    @abstractmethod
    async def connect(self) -> None: pass


    @abstractmethod
    async def close(self) -> None: pass

