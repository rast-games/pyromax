from typing import cast

from .Base import BaseMaxApiMethod


class DeleteUserCommentsMethod(BaseMaxApiMethod[bool]):
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        user_id: int,
        message_id: int | str,
    ) -> bool:
        """Delete a user's comments through the dedicated server operation."""
        if not self._max_api:
            raise RuntimeError("DeleteUserComments method not bound to MaxApi instance")

        return cast(
            bool,
            await self._max_api.mapper.call_method(
                type(self),
                chat_id=chat_id,
                post_id=post_id,
                user_id=user_id,
                message_id=message_id,
            ),
        )
