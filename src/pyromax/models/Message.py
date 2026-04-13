from __future__ import annotations
from typing import Optional, Literal, Any

from .base import BaseMaxObject
from .Files import BaseFileAttachment


class MessageLink(BaseMaxObject):
    type: str | None = None
    message: Message | None = None
    message_id: int | None = None


class Message(BaseMaxObject):
    message_id: int
    chat_id: int
    time: int
    type: str | None
    sender_id: int | None = None
    status: Literal['EDITED', 'REPLY', 'USER', 'OTHER'] = 'USER'
    text: str | None
    cid: int | None
    attaches: list[BaseFileAttachment] | None = None
    elements: list[dict[str, Any]] | None = None
    link: MessageLink | None = None


    async def answer(
            self,
            text: str | None = None,
            attaches: list[BaseFileAttachment] | None = None,
            link: MessageLink | None= None,
    ) -> Any:
        from ..methods import SendMessageMethod

        if self._max_api is None:
            raise RuntimeError('Message Model not linked to MaxApi instance')

        return await self._max_api(
            class_of_method=SendMessageMethod,
            text=text,
            chat_id=self.chat_id,
            attaches=attaches,
            link=link
        )


    async def reply(
            self,
            text: str | None = None,
            attaches: list[BaseFileAttachment] | None = None,
    ) -> Any:
        link = MessageLink(
            type='REPLY',
            message_id=self.message_id,
        )

        return await self.answer(
            text=text,
            attaches=attaches,
            link=link,
        )

# MessageLink.model_rebuild()