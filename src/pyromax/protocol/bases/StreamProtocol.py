from abc import abstractmethod
from typing import Generic

from .base import BaseMaxProtocol, T, R, TRANSPORT_TYPE


class StreamMaxProtocol(
    BaseMaxProtocol[T, R, TRANSPORT_TYPE], Generic[T, R, TRANSPORT_TYPE]
):

    @abstractmethod
    async def connect(self, gen: int) -> None:
        """Connect the protocol transport and start its response reader.

        :raises ConnectProtocolError: If the transport cannot be connected.


        :param gen: The current error gen.
        :type gen: int
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close."""
        pass

    @property
    @abstractmethod
    def transport(self) -> TRANSPORT_TYPE:
        """Transport.

        :returns: The resulting StreamTransport value.
        :rtype: StreamTransport
        """
        pass
