from typing import cast

from .Base import BaseMaxApiMethod


class SetChannelCommentsMethod(BaseMaxApiMethod[None]):
    async def __call__(self, chat_id: int, enabled: bool) -> None:
        """Enable or disable comments in a channel."""
        if not self._max_api:
            raise RuntimeError("SetChannelComments method not bound to MaxApi instance")

        return cast(
            None,
            await self._max_api.mapper.call_method(
                type(self),
                chat_id=chat_id,
                enabled=enabled,
            ),
        )
