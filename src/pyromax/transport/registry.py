from collections.abc import Callable

from .bases import BaseTransport

TRANSPORTS: dict[str, type[BaseTransport]] = {}


def register_transport(transport: str) -> Callable[[type[BaseTransport]], type[BaseTransport]]:
    global TRANSPORTS
    def wrapper(cls: type[BaseTransport]) -> type[BaseTransport]:
        TRANSPORTS[transport] = cls
        return cls
    return wrapper
