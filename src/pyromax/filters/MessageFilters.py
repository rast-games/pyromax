from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TYPE_CHECKING

from .base import Filter
from ..models import Message

if TYPE_CHECKING:
    from .. import MaxApi


class FromMeFilter(Filter):

    @property
    def work_with(self) -> tuple[type[Message]]:
        return (Message,)

    async def _check(self, msg: Message, max_api: MaxApi) -> bool | dict[str, Any]:
        if not max_api:
            self._logger.warn('Required argument(max_api) not provided')
        if max_api.id == msg.sender_id:
            return True
        return False


class ReplyToMessageFilter(Filter):

    @property
    def work_with(self) -> tuple[type[Message]]:
        return (Message,)


    async def _check(self, message: Message) -> bool | dict[str, Any]:
        if not message.link:
            return False

        if message.link.type != 'REPLY':
            return False

        return True


class MessageForwardFromFilter(Filter):
    @property
    def work_with(self) -> tuple[type[Message]]:
        return (Message,)

    async def _check(self, message: Message) -> bool | dict[str, Any]:
        if not message.link:
            return False

        if message.link.type != 'FORWARD':
            return False

        return True


class MessageRemovedFilter(Filter):
    @property
    def work_with(self) -> tuple[type[Message]]:
        return (Message,)

    async def _check(self, message: Message) -> bool | dict[str, Any]:
        if message.status == 'REMOVED':
            return True
        return False


class FromChatFilter(Filter):
    def __init__(self, chat_ids: int | Iterable[int]) -> None:
        super().__init__()
        if isinstance(chat_ids, int):
            chat_ids = (chat_ids,)
        self.chat_ids = chat_ids


    @property
    def work_with(self) -> tuple[type[Message]]:
        return (Message,)


    async def _check(self, msg: Message) -> bool | dict[str, Any]:
        return msg.chat_id in self.chat_ids
