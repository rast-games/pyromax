from __future__ import annotations

from collections.abc import Callable
from typing import Any, TYPE_CHECKING

from .base import BaseEncoding

if TYPE_CHECKING:
    pass

ENCODINGS = {}


def register_encoding(
    encoding: str,
) -> Callable[
    [type[BaseEncoding[Any, Any, Any, Any]]], type[BaseEncoding[Any, Any, Any, Any]]
]:
    """Register protocol.

    :param encoding: name of protocol.
    :type encoding: str
    :returns: The resulting Callable[[type[BaseMaxProtocol[Any, Any]]], type[BaseMaxProtocol[Any, Any]]] value.
    :rtype: Callable[[type[BaseMaxProtocol[Any, Any]]], type[BaseMaxProtocol[Any, Any]]]
    """
    global ENCODINGS

    def wrapper(
        cls: type[BaseEncoding[Any, Any, Any, Any]],
    ) -> type[BaseEncoding[Any, Any, Any, Any]]:
        """Wrapper.

        :returns: The resulting type[BaseMaxProtocol[Any, Any]] value.
        :rtype: type[BaseMaxProtocol[Any, Any]]
        """
        ENCODINGS[encoding] = cls
        return cls

    return wrapper
