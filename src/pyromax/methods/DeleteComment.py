from typing import cast

from .Base import BaseMaxApiMethod


class DeleteCommentMethod(BaseMaxApiMethod[bool]):
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        message_ids: list[int] | list[str],
        for_me: bool = False,
    ) -> bool:
        """Delete comments from a channel post."""
        if not self._max_api:
            raise RuntimeError("DeleteComment method not bound to MaxApi instance")

        return cast(
            bool,
            await self._max_api.mapper.call_method(
                type(self),
                chat_id=chat_id,
                post_id=post_id,
                message_ids=message_ids,
                for_me=for_me,
            ),
        )
