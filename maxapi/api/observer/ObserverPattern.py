from abc import ABC, abstractmethod


from maxapi.types import Update


class Observer(ABC):
    @abstractmethod
    async def update(self, update: Update) -> bool:
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


