from typing import cast

from .Base import BaseMaxApiMethod
from ..models.EmojiReaction import EmojiReaction


class RemoveCommentReactionMethod(BaseMaxApiMethod[EmojiReaction | None]):
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        message_id: int | str,
    ) -> EmojiReaction | None:
        """Remove the current account's reaction from a comment."""
        if not self._max_api:
            raise RuntimeError(
                "RemoveCommentReaction method not bound to MaxApi instance"
            )

        return cast(
            EmojiReaction | None,
            await self._max_api.mapper.call_method(
                type(self),
                chat_id=chat_id,
                post_id=post_id,
                message_id=message_id,
            ),
        )
