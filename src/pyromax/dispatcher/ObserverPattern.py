from __future__ import annotations
from abc import ABC, abstractmethod

from typing import TYPE_CHECKING, Any

# if TYPE_CHECKING:
#     from .event import Update
#     from .. import MaxApi


class Observer(ABC):
    @abstractmethod
    async def update(self, update: Any, data: dict[Any, Any] | None = None) -> bool:
        ...


class Subject(ABC):

    _observers: list[Observer]

    async def attach(self, observer: Observer) -> None:
        if observer not in self._observers:
            self._observers.append(observer)


    async def detach(self, observer: Observer) -> None:
        if observer in self._observers:
            self._observers.remove(observer)


    @abstractmethod
    async def notify(self, update: Any, data: dict[Any, Any] | None = None) -> bool:
        ...


