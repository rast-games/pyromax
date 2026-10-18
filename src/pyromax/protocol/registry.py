from __future__ import annotations

from collections.abc import Callable
from typing import Any, TYPE_CHECKING

from .bases import BaseMaxProtocol

if TYPE_CHECKING:
    pass

PROTOCOLS = {}


def register_protocol(
    protocol: str,
) -> Callable[[type[BaseMaxProtocol[Any, Any]]], type[BaseMaxProtocol[Any, Any]]]:
    """Register protocol.

    :param protocol: name of protocol.
    :type protocol: str
    :returns: The resulting Callable[[type[BaseMaxProtocol[Any, Any]]], type[BaseMaxProtocol[Any, Any]]] value.
    :rtype: Callable[[type[BaseMaxProtocol[Any, Any]]], type[BaseMaxProtocol[Any, Any]]]
    """
    global PROTOCOLS

    def wrapper(
        cls: type[BaseMaxProtocol[Any, Any]],
    ) -> type[BaseMaxProtocol[Any, Any]]:
        """Wrapper.

        :returns: The resulting type[BaseMaxProtocol[Any, Any]] value.
        :rtype: type[BaseMaxProtocol[Any, Any]]
        """
        PROTOCOLS[protocol] = cls
        return cls

    return wrapper
