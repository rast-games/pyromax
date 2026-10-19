from typing import cast

from .Base import BaseMaxApiMethod
from ..models.Attachments import BaseFileAttachment
from ..models.Message import Message


class SendCommentMethod(BaseMaxApiMethod[Message | None]):
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        text: str | None = None,
        reply_to: int | str | None = None,
        attachments: list[BaseFileAttachment] | None = None,
        *,
        notify: bool = True,
    ) -> Message | None:
        """Send a comment to a channel post."""
        if not self._max_api:
            raise RuntimeError("SendComment method not bound to MaxApi instance")

        return cast(
            Message | None,
            await self._max_api.mapper.call_method(
                type(self),
                chat_id=chat_id,
                post_id=post_id,
                text=text,
                reply_to=reply_to,
                attachments=attachments,
                notify=notify,
            ),
        )
