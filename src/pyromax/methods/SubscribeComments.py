from typing import cast

from .Base import BaseMaxApiMethod


class SubscribeCommentsMethod(BaseMaxApiMethod[None]):
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        subscribe: bool = True,
    ) -> None:
        """Subscribe to or unsubscribe from a post's comment events."""
        if not self._max_api:
            raise RuntimeError("SubscribeComments method not bound to MaxApi instance")

        return cast(
            None,
            await self._max_api.mapper.call_method(
                type(self),
                chat_id=chat_id,
                post_id=post_id,
                subscribe=subscribe,
            ),
        )
