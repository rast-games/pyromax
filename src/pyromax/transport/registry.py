from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .bases import BaseTransport

if TYPE_CHECKING:
    pass

TRANSPORTS = {}


def register_transport(
    transport: str,
) -> Callable[[type[BaseTransport[Any]]], type[BaseTransport[Any]]]:
    """Register transport.

    :param transport: name of the transport.
    :type transport: str
    :returns: The decorator Callable[[type[BaseTransport]], type[BaseTransport]].
    :rtype: Callable[[type[BaseTransport]], type[BaseTransport]]
    """
    global TRANSPORTS

    def wrapper(cls: type[BaseTransport[Any]]) -> type[BaseTransport[Any]]:
        """Wrapper.

        :param cls: transport class
        :type cls: type[BaseTransport]
        :returns: The resulting type[BaseTransport].
        :rtype: type[BaseTransport]
        """
        TRANSPORTS[transport] = cls
        return cls

    return wrapper
