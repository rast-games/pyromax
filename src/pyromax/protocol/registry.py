from collections.abc import Callable
from typing import Any

from .bases import BaseMaxProtocol

PROTOCOLS = {}


def register_protocol(protocol: str) -> Callable[[type[BaseMaxProtocol[Any, Any]]], type[BaseMaxProtocol[Any, Any]]]:
    global PROTOCOLS
    def wrapper(cls: type[BaseMaxProtocol[Any, Any]]) -> type[BaseMaxProtocol[Any, Any]]:
        PROTOCOLS[protocol] = cls
        return cls
    return wrapper
