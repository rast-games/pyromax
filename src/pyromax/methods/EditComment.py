from typing import cast

from .Base import BaseMaxApiMethod
from ..models.Attachments import BaseFileAttachment
from ..models.Message import Message


class EditCommentMethod(BaseMaxApiMethod[Message]):
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        message_id: int | str,
        text: str | None = None,
        attachments: list[BaseFileAttachment] | None = None,
    ) -> Message:
        """Edit a comment on a channel post."""
        if not self._max_api:
            raise RuntimeError("EditComment method not bound to MaxApi instance")

        return cast(
            Message,
            await self._max_api.mapper.call_method(
                type(self),
                chat_id=chat_id,
                post_id=post_id,
                message_id=message_id,
                text=text,
                attachments=attachments,
            ),
        )
