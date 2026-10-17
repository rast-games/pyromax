from __future__ import annotations
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional

from .Base import BaseMaxApiMethod
from ..models.Message import Message

if TYPE_CHECKING:
    from ..models import BaseFileAttachment


class SendMessageMethod(BaseMaxApiMethod[Optional[Message]]):
    async def __call__(
        self,
        *,
        chat_id: int,
        text: str | None = None,
        attaches: list[BaseFileAttachment] | None = None,
        notify: bool = True,
        send_at: datetime | timedelta | int | None = None,
        **kwargs: Any,
    ) -> Message | None:
        """Execute the send message MAX API method.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param text: Message or textual content.
        :type text: str | None
        :param attaches: Attachments associated with the message.
        :type attaches: list[BaseFileAttachment] | None
        :param notify: Whether MAX should notify affected users.
        :type notify: bool
        :param send_at: Scheduled send time as an absolute datetime, a relative
            timedelta, or Unix time in seconds. None and 0 send immediately.
        :type send_at: datetime | timedelta | int | None
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting Message | None value.
        :rtype: Message | None
        :raises RuntimeError: If sendMessage method not bound to MaxApi instance.
        """
        if not attaches:
            attaches = []

        if not self._max_api:
            raise RuntimeError("SendMessage method not bound to MaxApi instance")
        return await self._max_api.mapper.send_message(
            chat_id=chat_id,
            text=text,
            attaches=attaches,
            notify=notify,
            send_at=send_at,
            **kwargs,
        )

        # return await self._max_api.mapper.call_method(
        #     type(self),
        #     chat_id=chat_id,
        #     text=text,
        #     attaches=attaches,
        #     **kwargs,
        # )
