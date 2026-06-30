from __future__ import annotations

from collections.abc import Callable
from typing import Any, TYPE_CHECKING

from .bases import BaseMapper

if TYPE_CHECKING:
    from ..mixins import AsyncConstructorType

MAPPERS = {}


def register_mapper(mapper: str) -> Callable[[type[BaseMapper[Any, Any]]], type[BaseMapper[Any, Any]]]:
    global MAPPERS
    def wrapper(cls: type[BaseMapper[Any, Any]]) -> type[BaseMapper[Any, Any]]:
        MAPPERS[mapper] = cls
        return cls
    return wrapper
