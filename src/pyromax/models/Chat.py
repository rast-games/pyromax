from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, Any, overload, cast

from pydantic import Field

from .base import BaseMaxObject
from .Attachments import BaseFileAttachment
from .Message import Message, MessageLink


class Chat(BaseMaxObject):
    id: int
    type: Literal["DIALOG", "CHAT", "CHANNEL"]
    status: str
    owner: int
    participants: dict[int, int] = Field(default_factory=dict)
    title: str | None = None
    base_raw_icon_url: str | None = None
    base_icon_url: str | None = None
    last_message: Message | None = None
    last_event_time: int = 0
    last_delayed_update_time: int = 0
    last_fire_delayed_error_time: int = 0
    created: int = 0
    new_messages: int = 0
    link: str | None = None
    access: Literal["PUBLIC", "PRIVATE", "SECRET"] | None = None
    restrictions: int | None = None
    pinned_message: Message | None = None
    participants_count: int = 0
    description: str | None = None
    options: dict[str, bool] | int | None = None
    join_time: int = 0
    invited_by: int | None = None
    modified: int = 0
    messages_count: int = 0
    has_bots: bool | None = None
    prev_message_id: int | None = None
    admin_participants: dict[int, dict[Any, Any]] = Field(default_factory=dict)
    admins: list[int] = Field(default_factory=list)
    cid: int | None = None

    async def answer(
        self,
        text: str | None = None,
        link: MessageLink | None = None,
        attaches: list[BaseFileAttachment] | None = None,
        notify: bool = True,
    ) -> Message | None:
        """Answer.

        :param text: Message or textual content.
        :type text: str | None
        :param link: Message link to another message(s).
        :type link: MessageLink | None
        :param attaches: Attachments associated with the message.
        :type attaches: list[BaseFileAttachment] | None
        :param notify: Whether MAX should notify affected users.
        :type notify: bool
        :returns: The resulting Message | None value.
        :rtype: Message | None
        """
        return await self.max_api.send_message(
            chat_id=self.id,
            text=text or "",
            link=link,
            attaches=attaches,
            notify=notify,
        )

    @overload
    async def history(
        self,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = ...,
        item_type: Literal["DELAYED", "REGULAR"] = ...,
        get_chat: Literal[False] = False,
        get_messages: Literal[True] = True,
        interactive: bool = ...,
    ) -> list[Message]:
        """History.

        :param forward: The forward value.
        :type forward: int
        :param backward: The backward value.
        :type backward: int
        :param backward_time: The backward time value.
        :type backward_time: int
        :param forward_time: The forward time value.
        :type forward_time: int
        :param from_time: The from time value.
        :type from_time: int | None
        :param item_type: Literal['DELAYED', 'REGULAR'] instance to process.
        :type item_type: Literal['DELAYED', 'REGULAR']
        :param get_chat: The get chat value.
        :type get_chat: bool
        :param get_messages: Literal[True] instance to process.
        :type get_messages: Literal[True]
        :param interactive: The interactive value.
        :type interactive: bool
        :returns: The resulting collection.
        :rtype: list[Message]
        """
        pass

    @overload
    async def history(
        self,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = None,
        item_type: Literal["DELAYED", "REGULAR"] = ...,
        get_chat: Literal[True] = True,
        get_messages: Literal[True] = True,
        interactive: bool = ...,
    ) -> tuple[list[Message], Chat | None]: ...

    @overload
    async def history(
        self,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = None,
        item_type: Literal["DELAYED", "REGULAR"] = ...,
        get_chat: Literal[False] = False,
        get_messages: Literal[False] = False,
        interactive: bool = ...,
    ) -> list[str | int]:
        """History.

        :param forward: The forward value.
        :type forward: int
        :param backward: The backward value.
        :type backward: int
        :param backward_time: The backward time value.
        :type backward_time: int
        :param forward_time: The forward time value.
        :type forward_time: int
        :param from_time: The from time value.
        :type from_time: int | None
        :param item_type: Literal['DELAYED', 'REGULAR'] instance to process.
        :type item_type: Literal['DELAYED', 'REGULAR']
        :param get_chat: The get chat value.
        :type get_chat: bool
        :param get_messages: Literal[False] instance to process.
        :type get_messages: Literal[False]
        :param interactive: The interactive value.
        :type interactive: bool
        :returns: The resulting collection.
        :rtype: list[str | int]
        """
        pass

    @overload
    async def history(
        self,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = None,
        item_type: Literal["DELAYED", "REGULAR"] = ...,
        get_chat: Literal[True] = True,
        get_messages: Literal[False] = False,
        interactive: bool = ...,
    ) -> tuple[list[str | int], Chat | None]: ...

    @overload
    async def history(
        self,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = None,
        item_type: Literal["DELAYED", "REGULAR"] = ...,
        get_chat: bool = ...,
        get_messages: bool = ...,
        interactive: bool = ...,
    ) -> (
        list[Message]
        | list[str | int]
        | tuple[list[Message] | list[str | int], Chat | None]
    ):
        """History.

        :param forward: The forward value.
        :type forward: int
        :param backward: The backward value.
        :type backward: int
        :param backward_time: The backward time value.
        :type backward_time: int
        :param forward_time: The forward time value.
        :type forward_time: int
        :param from_time: The from time value.
        :type from_time: int | None
        :param item_type: Literal['DELAYED', 'REGULAR'] instance to process.
        :type item_type: Literal['DELAYED', 'REGULAR']
        :param get_chat: The get chat value.
        :type get_chat: bool
        :param get_messages: The get messages value.
        :type get_messages: bool
        :param interactive: The interactive value.
        :type interactive: bool
        :returns: The resulting collection.
        :rtype: list[Message] | list[str | int] | tuple[list[Message] | list[str | int], Chat | None]
        """
        pass

    async def history(
        self,
        forward: int = 0,
        backward: int = 40,
        backward_time: int = 0,
        forward_time: int = 0,
        from_time: int | None = None,
        item_type: Literal["DELAYED", "REGULAR"] = "REGULAR",
        get_chat: bool = False,
        get_messages: bool = True,
        interactive: bool = False,
    ) -> (
        list[Message]
        | list[str | int]
        | tuple[list[Message] | list[str | int], Chat | None]
    ):
        """Retrieve chat history.

        :param forward: How many messages to load ahead from ``from_time``.
        :type forward: int
        :param backward: How many messages to load back from ``from_time``.
        :type backward: int
        :param backward_time: Look-back time window in milliseconds.
        :type backward_time: int
        :param forward_time: Forward time window in milliseconds.
        :type forward_time: int
        :param from_time: The reference point in Unix time (milliseconds). If ``None``, the current moment is used.
        :type from_time: int | None
        :param item_type: History item type.
        :type item_type: Literal['DELAYED', 'REGULAR']
        :param get_chat: Request chat data along with the history.
        :type get_chat: bool
        :param get_messages: The get messages value.
        :type get_messages: bool
        :param interactive: Request the messages themselves.
        :type interactive: bool
        :returns: History items, paired with the requested chat when ``get_chat`` is true.
        :rtype: list[Message] | list[str | int] | tuple[list[Message] | list[str | int], Chat | None]
        """

        return await self.max_api.get_chat_history(
            chat_id=self.id,
            forward=forward,
            backward=backward,
            backward_time=backward_time,
            forward_time=forward_time,
            from_time=from_time,
            item_type=item_type,
            get_chat=get_chat,
            interactive=interactive,
            get_messages=get_messages,
        )

    async def get_message(self, message_id: int | str) -> Message | None:
        """Retrieve message.

        :param message_id: Identifier of the message.
        :type message_id: int | str
        :returns: The resulting Message | None value.
        :rtype: Message | None
        """
        return await self.max_api.get_message(
            chat_id=self.id,
            message_id=message_id,
        )

    async def get_messages(
        self, message_ids: Iterable[int] | Iterable[str]
    ) -> list[Message]:
        """Retrieve messages.

        :param message_ids: Identifiers of the messages.
        :type message_ids: Iterable[int] | Iterable[str]
        :returns: The resulting collection.
        :rtype: list[Message]
        """
        return await self.max_api.get_messages(
            chat_id=self.id,
            message_ids=message_ids,
        )

    async def leave(self) -> None | Message:
        """leave the chat

        :raises RuntimeError: if chat is DIALOG
        :raises ValueError: if chat type is unknown
        """

        if self.type == "DIALOG":
            raise RuntimeError("Cannot leave dialog")
        elif self.type == "CHAT":
            return await self.max_api.leave_group(
                chat_id=self.id,
            )
        elif self.type == "CHANNEL":
            return await self.max_api.leave_channel(
                chat_id=self.id,
            )
        raise ValueError("Unknown chat type=%s", self.type)

    async def delete(self, for_all: bool = True) -> None:
        """Delete.

        :param for_all: Delete only for the current account.
        :type for_all: bool
        """
        return await self.max_api.delete_chat(
            chat_id=self.id,
            for_all=for_all,
        )

    async def invite(
        self, user_ids: list[int], show_history: bool = True
    ) -> Chat | None:
        """invite users to chat

        :raises ValueError: if try to invite users to unknown chat
        :raises RuntimeError: if max_api not linked to chat instance

        :param user_ids: Identifiers of the users.
        :type user_ids: list[int]
        :param show_history: Show message history to new members.
        :type show_history: bool
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """

        if self.type == "CHAT":
            return await self.max_api.invite_users_to_group(
                chat_id=self.id,
                user_ids=user_ids,
                show_history=show_history,
            )
        elif self.type == "CHANNEL":
            return await self.max_api.invite_users_to_group(
                chat_id=self.id,
                user_ids=user_ids,
                show_history=show_history,
            )

        raise ValueError("Unknown chat type=%s", self.type)

    async def remove_users(
        self,
        user_ids: list[int],
        clean_msg_period: int = 0,
    ) -> Chat | None:
        """Remove users.

        :param user_ids: Identifiers of the users.
        :type user_ids: list[int]
        :param clean_msg_period: Cleanup period for messages from removed participants.
        :type clean_msg_period: int
        """
        return await self.max_api.remove_users_from_group(
            chat_id=self.id,
            user_ids=user_ids,
            clean_msg_period=clean_msg_period,
        )

    async def pin_message(self, message_id: str | int, notify_pin: bool = True) -> None:
        """Pin message.

        :param message_id: Identifier of the message.
        :type message_id: str | int
        :param notify_pin: Whether MAX should notify affected users.
        :type notify_pin: bool
        """
        return await self.max_api.pin_message(
            chat_id=self.id,
            message_id=message_id,
            notify=notify_pin,
        )

    async def update_settings(
        self,
        all_can_pin_message: bool | None = None,
        only_owner_can_change_icon_title: bool | None = None,
        only_admin_can_add_member: bool | None = None,
        only_admin_can_call: bool | None = None,
        members_can_see_private_link: bool | None = None,
    ) -> Chat | None:
        """Update settings.

        :param all_can_pin_message: The all can pin message.
        :type all_can_pin_message: bool | None
        :param only_owner_can_change_icon_title: The only owner can change icon title.
        :type only_owner_can_change_icon_title: bool | None
        :param only_admin_can_add_member: The only admin can add member.
        :type only_admin_can_add_member: bool | None
        :param only_admin_can_call: The only admin can call.
        :type only_admin_can_call: bool | None
        :param members_can_see_private_link: The members can see private link.
        :type members_can_see_private_link: bool | None
        """
        return await self.max_api.change_group_settings(
            chat_id=self.id,
            all_can_pin_message=all_can_pin_message,
            only_admin_can_add_member=only_admin_can_add_member,
            only_admin_can_call=only_admin_can_call,
            members_can_see_private_link=members_can_see_private_link,
            only_owner_can_change_icon_title=only_owner_can_change_icon_title,
        )

    async def revoke_invite_link(self) -> Chat:
        """Revoke invite link.

        :returns: The resulting Chat value.
        :rtype: Chat
        """
        return await self.max_api.revoke_invite_link(chat_id=self.id)

    @property
    def is_dialog(self) -> bool:
        """Return whether dialog.

        :returns: ``True`` when the requested condition is satisfied; otherwise ``False``.
        :rtype: bool
        """
        return self.type == "DIALOG"

    @property
    def is_group(self) -> bool:
        """Return whether group.

        :returns: ``True`` when the requested condition is satisfied; otherwise ``False``.
        :rtype: bool
        """
        return self.type == "CHAT"

    @property
    def is_channel(self) -> bool:
        """Return whether channel.

        :returns: ``True`` when the requested condition is satisfied; otherwise ``False``.
        :rtype: bool
        """
        return self.type == "CHANNEL"
