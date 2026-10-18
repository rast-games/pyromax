from __future__ import annotations
from abc import ABC, abstractmethod

from typing import Any

# if TYPE_CHECKING:
#     from .event import Update
#     from .. import MaxApi


class Observer(ABC):
    @abstractmethod
    async def update(self, update: Any, data: dict[Any, Any] | None = None) -> bool:
        """Update.

        :param update: Incoming update to process.
        :type update: Any
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any] | None
        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        """
        ...


class Subject(ABC):

    _observers: list[Observer]

    async def attach(self, observer: Observer) -> None:
        """Attach.

        :param observer: Observer instance to process.
        :type observer: Observer
        """
        if observer not in self._observers:
            self._observers.append(observer)

    async def detach(self, observer: Observer) -> None:
        """Detach.

        :param observer: Observer instance to process.
        :type observer: Observer
        """
        if observer in self._observers:
            self._observers.remove(observer)

    @abstractmethod
    async def notify(self, update: Any, data: Any) -> bool:
        """Notify.

        :param update: Incoming update to process.
        :type update: Any
        :param data: Contextual data passed through the processing pipeline.
        :type data: Any
        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        """
        ...
