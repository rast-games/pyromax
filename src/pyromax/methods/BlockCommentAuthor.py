from typing import cast

from .Base import BaseMaxApiMethod


class BlockCommentAuthorMethod(BaseMaxApiMethod[bool]):
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        user_ids: list[int],
        message_id: int | str,
        clean_msg_period: int = 0,
    ) -> bool:
        """Block comment authors and optionally remove their comments."""
        if not self._max_api:
            raise RuntimeError("BlockCommentAuthor method not bound to MaxApi instance")

        return cast(
            bool,
            await self._max_api.mapper.call_method(
                type(self),
                chat_id=chat_id,
                post_id=post_id,
                user_ids=user_ids,
                message_id=message_id,
                clean_msg_period=clean_msg_period,
            ),
        )
