from abc import abstractmethod
from typing import Generic

from .base import BaseMaxProtocol, RequestType, ResponseType, TRANSPORT_TYPE


class StreamMaxProtocol(
    BaseMaxProtocol[RequestType, ResponseType, TRANSPORT_TYPE],
    Generic[RequestType, ResponseType, TRANSPORT_TYPE],
):

    @abstractmethod
    async def connect(self) -> None:
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
