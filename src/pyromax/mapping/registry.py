from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .bases.BaseMapper import BaseMapper

MAPPERS = {}


def register_mapper(
    mapper: str,
) -> Callable[[type[BaseMapper[Any, Any]]], type[BaseMapper[Any, Any]]]:
    """Register mapper.

    :param mapper: Mapper backend or mapper instance.
    :type mapper: str
    :returns: The resulting Callable[[type[BaseMapper[Any, Any]]], type[BaseMapper[Any, Any]]] value.
    :rtype: Callable[[type[BaseMapper[Any, Any]]], type[BaseMapper[Any, Any]]]
    """
    global MAPPERS

    def wrapper(cls: type[BaseMapper[Any, Any]]) -> type[BaseMapper[Any, Any]]:
        """Wrapper.

        :returns: The resulting type[BaseMapper[Any, Any]] value.
        :rtype: type[BaseMapper[Any, Any]]
        """
        MAPPERS[mapper] = cls
        return cls

    return wrapper
