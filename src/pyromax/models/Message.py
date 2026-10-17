from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional, Literal, Any, TYPE_CHECKING

from .base import BaseMaxObject
from .ReadState import ReadState
from .EmojiReaction import EmojiReaction
from .Attachments import BaseFileAttachment


class MessageLink(BaseMaxObject):
    type: str | None = None
    message: Message | None = None
    message_id: int | str | None = None
    chat_id: int | None = None


class DelayedAttributes(BaseMaxObject):
    time_to_fire: int
    notify_sender: bool
    notify_opponents: bool | None = None


class Message(BaseMaxObject):
    message_id: int | str
    chat_id: int
    time: int
    type: str | None
    sender_id: int | None = None
    status: Literal["EDITED", "REPLY", "USER", "REMOVED", "SHARE", "OTHER"] = "USER"
    text: str | None
    cid: int | None
    elements: list[dict[str, Any]] | None = None
    link: MessageLink | None = None
    delayed_attributes: DelayedAttributes | None = None

    if TYPE_CHECKING:
        from .Attachments import (
            VideoAttachment,
            VoiceAttachment,
            VideoNoteAttachment,
            FileAttachment,
            PhotoAttachment,
            BaseFileAttachment,
        )
        from .Poll import Poll

        from typing import Never

        attaches: list[  # type: ignore[valid-type]
            VideoAttachment
            | VideoNoteAttachment
            | VoiceAttachment
            | FileAttachment
            | PhotoAttachment
            | Poll[Never]
            | Any
        ]
    else:
        attaches: list[Any] | None = None

    async def answer(
        self,
        text: str | None = None,
        attaches: list[BaseFileAttachment] | None = None,
        link: MessageLink | None = None,
        *,
        notify: bool = True,
        send_at: datetime | timedelta | int | None = None,
    ) -> Any:
        """Answer.

        :param text: Message or textual content.
        :type text: str | None
        :param attaches: Attachments associated with the message.
        :type attaches: list[BaseFileAttachment] | None
        :param link: Invite, message, or resource link.
        :type link: MessageLink | None
        :param notify: Whether MAX should notify affected users.
        :type notify: bool
        :param send_at: Scheduled send time as an absolute datetime, a relative
            timedelta, or Unix time in seconds. None and 0 send immediately.
        :type send_at: datetime | timedelta | int | None
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        """
        from ..methods import SendMessageMethod

        return await self.max_api(
            class_of_method=SendMessageMethod,
            text=text,
            chat_id=self.chat_id,
            attaches=attaches,
            link=link,
            notify=notify,
            send_at=send_at,
        )

    async def reply(
        self,
        text: str | None = None,
        attaches: list[BaseFileAttachment] | None = None,
        *,
        notify: bool = True,
        send_at: datetime | timedelta | int | None = None,
    ) -> Any:
        """Reply.

        :param text: Message or textual content.
        :type text: str | None
        :param attaches: Attachments associated with the message.
        :type attaches: list[BaseFileAttachment] | None
        :param notify: Whether MAX should notify affected users.
        :type notify: bool
        :param send_at: Scheduled send time as an absolute datetime, a relative
            timedelta, or Unix time in seconds. None and 0 send immediately.
        :type send_at: datetime | timedelta | int | None
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        """
        link = MessageLink(
            type="REPLY",
            message_id=self.message_id,
        )

        return await self.answer(
            text=text,
            attaches=attaches,
            link=link,
            notify=notify,
            send_at=send_at,
        )

    async def forward(
        self,
        chat_id: int,
        *,
        notify: bool = True,
    ) -> Message | None:
        """Forward.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param notify: Whether MAX should notify affected users.
        :type notify: bool
        :returns: The resulting Message | None value.
        :rtype: Message | None
        """
        return await self.max_api.forward_message(
            from_chat_id=self.chat_id,
            to_chat_id=chat_id,
            message_id=self.message_id,
            notify=notify,
        )

    async def pin(self, notify_pin: bool = True) -> None:
        """Pin.

        :param notify_pin: Whether MAX should notify affected users.
        :type notify_pin: bool
        """
        return await self.max_api.pin_message(
            chat_id=self.chat_id,
            message_id=self.message_id,
            notify=notify_pin,
        )

    async def edit(
        self,
        text: str | None = None,
        attachments: list[BaseFileAttachment] | None = None,
    ) -> Message:
        """Edit.

        :param text: Message or textual content.
        :type text: str | None
        :param attachments: Attachments associated with the message.
        :type attachments: list[BaseFileAttachment] | None
        :returns: The resulting Message value.
        :rtype: Message
        """
        return await self.max_api.edit_message(
            chat_id=self.chat_id,
            message_id=self.message_id,
            text=text,
            attachments=attachments,
        )

    async def delete(self, for_me: bool = False) -> None:
        """Delete.

        :param for_me: Delete only for the current account.
        :type for_me: bool
        """
        msg_ids: list[int] | list[str]
        if isinstance(self.message_id, str):
            msg_ids = [self.message_id]
        else:
            msg_ids = [self.message_id]
        return await self.max_api.delete_messages(
            chat_id=self.chat_id,
            message_ids=msg_ids,
            for_me=for_me,
        )

    async def read(self) -> ReadState:
        """Read.

        :returns: The resulting ReadState value.
        :rtype: ReadState
        """
        return await self.max_api.read_message(
            chat_id=self.chat_id,
            message_id=self.message_id,
        )

    async def react(self, reaction: str) -> EmojiReaction | None:
        """React.

        :param reaction: The reaction value.
        :type reaction: str
        :returns: The resulting EmojiReaction | None value.
        :rtype: EmojiReaction | None
        """
        return await self.max_api.add_reaction(
            chat_id=self.chat_id,
            message_id=self.message_id,
            reaction_id=reaction,
        )

    async def unreact(self) -> EmojiReaction | None:
        """Unreact.

        :returns: The resulting EmojiReaction | None value.
        :rtype: EmojiReaction | None
        """
        return await self.max_api.remove_reaction(
            chat_id=self.chat_id,
            message_id=self.message_id,
        )

    async def get_reactions(self) -> dict[str, EmojiReaction] | None:
        """Retrieve reactions.

        :returns: The resulting dict[str, EmojiReaction] | None value.
        :rtype: dict[str, EmojiReaction] | None
        """
        msg_ids: list[int] | list[str]
        if isinstance(self.message_id, str):
            msg_ids = [self.message_id]
        else:
            msg_ids = [self.message_id]
        return await self.max_api.get_reactions(
            chat_id=self.chat_id,
            message_ids=msg_ids,
        )
