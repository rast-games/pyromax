from __future__ import annotations
from typing import TYPE_CHECKING, Any

from .Base import BaseMaxApiMethod
from ..models import Message

if TYPE_CHECKING:
    from ..models import BaseFileAttachment


class SendMessageMethod(BaseMaxApiMethod[Message]):
    async def __call__(
            self,
            *,
            chat_id: int,
            text: str | None = None,
            attaches: list[BaseFileAttachment] | None = None,
            **kwargs: Any
    ) -> Any:
        if not attaches:
            attaches = []

        if not self._max_api:
            raise RuntimeError('SendMessage method not bound to MaxApi instance')
        return await self._max_api.mapper.send_message(
            chat_id=chat_id,
            text=text,
            attaches=attaches,
            **kwargs
        )