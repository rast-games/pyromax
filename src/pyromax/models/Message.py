from __future__ import annotations
from typing import Optional, Literal

from .base import BaseMaxObject
from ..methods import SendMessageMethod
from .Files import BaseFileAttachment


class MessageLink(BaseMaxObject):
    type: str | None = None
    message: Optional['Message'] = None
    message_id: int | None = None


class Message(BaseMaxObject):
    message_id: int
    chat_id: int
    time: int
    sender_id: int | None = None
    type: str | None
    status: Literal['EDITED', 'REPLY', 'USER', 'OTHER'] = 'USER'
    text: str | None
    cid: int | None
    attaches: list | None = None
    elements: list[dict] | None = None
    link: MessageLink | None = None


    async def answer(
            self,
            text: str = None,
            attaches: list[BaseFileAttachment] = None,
            link: MessageLink = None,
    ):
        return await self._max_api(
            class_of_method=SendMessageMethod,
            text=text,
            chat_id=self.chat_id,
            attaches=attaches,
            link=link
        )


    async def reply(
            self,
            text: str = None,
            attaches: list[BaseFileAttachment] = None,
    ):
        link = MessageLink(
            type='REPLY',
            message_id=self.message_id,
        )

        return await self.answer(
            text=text,
            attaches=attaches,
            link=link,
        )

MessageLink.model_rebuild()