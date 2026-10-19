from typing import cast

from .Base import BaseMaxApiMethod
from ..models.Message import Message


class GetCommentMethod(BaseMaxApiMethod[Message | None]):
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        message_id: int | str,
    ) -> Message | None:
        """Get one comment from a channel post."""
        if not self._max_api:
            raise RuntimeError("GetComment method not bound to MaxApi instance")

        return cast(
            Message | None,
            await self._max_api.mapper.call_method(
                type(self),
                chat_id=chat_id,
                post_id=post_id,
                message_id=message_id,
            ),
        )
