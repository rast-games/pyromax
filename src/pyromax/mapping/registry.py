from collections.abc import Callable
from typing import Any

from .bases import BaseMapper

MAPPERS = {}


def register_mapper(mapper: str) -> Callable[[type[BaseMapper[Any]]], type[BaseMapper[Any]]]:
    global MAPPERS
    def wrapper(cls: type[BaseMapper[Any]]) -> type[BaseMapper[Any]]:
        MAPPERS[mapper] = cls
        return cls
    return wrapper
