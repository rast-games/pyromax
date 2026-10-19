from typing import cast

from .Base import BaseMaxApiMethod
from ..models.Message import Message


class GetCommentsMethod(BaseMaxApiMethod[list[Message]]):
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        message_ids: list[int | str],
    ) -> list[Message]:
        """Get specific comments from a channel post."""
        if not self._max_api:
            raise RuntimeError("GetComments method not bound to MaxApi instance")

        return cast(
            list[Message],
            await self._max_api.mapper.call_method(
                type(self),
                chat_id=chat_id,
                post_id=post_id,
                message_ids=message_ids,
            ),
        )
