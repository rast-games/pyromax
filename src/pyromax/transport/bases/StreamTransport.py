from abc import abstractmethod
from typing import Any

from .base import BaseTransport, ENCODING_TYPE

class StreamTransport(BaseTransport[ENCODING_TYPE]):
    @abstractmethod
    async def connect(self, **kwargs: Any) -> None:
        """Connect.

        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any

        :raises ConnectTransportError: if connect fails
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close.


        :raises CloseTransportError: if close fails
        """
        pass

    @abstractmethod
    async def send(self, request: Any) -> None:
        """Send.

        :param request: Protocol request envelope to populate or send.
        :type request: Any

        :raises SendingTransportError: if send fails
        """
        pass

    @abstractmethod
    async def recv(self) -> Any:
        """Recv.

        :returns: The value returned by the backend.
        :rtype: Any

        :raises ReceivingTransportError: if recv fails
        """
        pass

    @property
    @abstractmethod
    def connected(self) -> bool: ...
