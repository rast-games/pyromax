from typing import cast

from .Base import BaseMaxApiMethod
from ..models.Message import Message


class FetchCommentsMethod(BaseMaxApiMethod[list[Message]]):
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        from_: int | None = None,
        backward: int = 30,
        get_messages: bool = True,
        forward: int = 0,
    ) -> list[Message]:
        """Fetch comments for a channel post."""
        if not self._max_api:
            raise RuntimeError("FetchComments method not bound to MaxApi instance")

        return cast(
            list[Message],
            await self._max_api.mapper.call_method(
                type(self),
                chat_id=chat_id,
                post_id=post_id,
                from_=from_,
                backward=backward,
                get_messages=get_messages,
                forward=forward,
            ),
        )
