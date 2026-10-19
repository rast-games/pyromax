from typing import cast

from .Base import BaseMaxApiMethod
from ..models import CommentsInfoUpdate


class GetCommentsInfoMethod(BaseMaxApiMethod[list[CommentsInfoUpdate]]):
    async def __call__(
        self,
        chat_id: int,
        post_ids: list[int],
    ) -> list[CommentsInfoUpdate]:
        """Get comment counters for channel posts."""
        if not self._max_api:
            raise RuntimeError("GetCommentsInfo method not bound to MaxApi instance")

        return cast(
            list[CommentsInfoUpdate],
            await self._max_api.mapper.call_method(
                type(self),
                chat_id=chat_id,
                post_ids=post_ids,
            ),
        )
