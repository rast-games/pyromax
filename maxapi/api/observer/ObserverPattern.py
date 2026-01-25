from abc import ABC, abstractmethod


from maxapi.types import Update
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .. import MaxApi


class Observer(ABC):
    @abstractmethod
    async def update(self, update: Update, max_api: 'MaxApi') -> bool:
        ...


class Subject(ABC):


    async def attach(self, handler: Observer) -> None:
        if handler not in self._handlers:
            self._handlers.append(handler)


    async def detach(self, handler: Observer) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)


    @abstractmethod
    async def notify(self, update: Update) -> None:
        ...


