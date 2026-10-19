from collections.abc import Iterable
from typing import cast

from ...methods import (
    CreateGroupMethod,
    InviteUsersToGroupMethod,
    RemoveUsersFromGroupMethod,
    ChangeGroupSettingsMethod,
    ChangeGroupProfileMethod,
    JoinGroupMethod,
    JoinChannelMethod,
    ResolveGroupByLinkMethod,
    RevokeInviteLinkMethod,
    GetChatsMethod,
    LeaveChannelMethod,
    LeaveGroupMethod,
    FetchChatsMethod,
    GetJoinRequestsMethod,
    ConfirmJoinRequestsMethod,
    DeclineJoinRequestsMethod,
    DeleteChatMethod,
    AddAdminMethod,
    SetChannelCommentsMethod,
)
from ...models import (
    Message,
    Chat,
    Member,
    ChannelPermissions,
)
from .CoreMixinsProtocol import CoreMixinsProtocol


class ChatMixin(CoreMixinsProtocol):
    async def create_group(
        self,
        title: str,
        participant_ids: list[int] | None = None,
        notify: bool = True,
        chat_type: str = "CHAT",
        event: str = "new",
        typeof: str = "CONTROL",
    ) -> tuple[Chat, Message] | tuple[None, None]:
        """Create group.

        :param title: The title value.
        :type title: str
        :param participant_ids: Identifiers of the participant objects.
        :type participant_ids: list[int] | None
        :param notify: Whether MAX should notify affected users.
        :type notify: bool
        :param chat_type: The chat type value.
        :type chat_type: str
        :param event: Incoming event to process.
        :type event: str
        :param typeof: Attachment class that determines the upload type.
        :type typeof: str
        :returns: The resulting tuple[Chat, Message] | tuple[None, None] value.
        :rtype: tuple[Chat, Message] | tuple[None, None]
        """

        return cast(
            tuple[Chat, Message] | tuple[None, None],
            await self(
                CreateGroupMethod,
                title=title,
                participant_ids=participant_ids,
                notify=notify,
                chat_type=chat_type,
                event=event,
                typeof=typeof,
            ),
        )

    async def invite_users_to_group(
        self,
        chat_id: int,
        user_ids: list[int],
        show_history: bool = True,
    ) -> Chat | None:
        """Invite users to group.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param user_ids: Identifiers of the users.
        :type user_ids: list[int]
        :param show_history: Show message history to new members.
        :type show_history: bool
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """

        return cast(
            Chat | None,
            await self(
                InviteUsersToGroupMethod,
                chat_id=chat_id,
                user_ids=user_ids,
                show_history=show_history,
            ),
        )

    async def remove_users_from_group(
        self,
        chat_id: int,
        user_ids: list[int] | list[str],
        clean_msg_period: int,
    ) -> Chat | None:
        """Remove users from group.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param user_ids: Identifiers of the users.
        :type user_ids: list[int] | list[str]
        :param clean_msg_period: Cleanup period for messages from removed participants.
        :type clean_msg_period: int
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """

        return cast(
            Chat | None,
            await self(
                RemoveUsersFromGroupMethod,
                chat_id=chat_id,
                user_ids=user_ids,
                clean_msg_period=clean_msg_period,
            ),
        )

    async def change_group_settings(
        self,
        chat_id: int,
        all_can_pin_message: bool | None = None,
        only_owner_can_change_icon_title: bool | None = None,
        only_admin_can_add_member: bool | None = None,
        only_admin_can_call: bool | None = None,
        members_can_see_private_link: bool | None = None,
    ) -> Chat | None:
        """Change group settings.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param all_can_pin_message: All participants can pin messages.
        :type all_can_pin_message: bool | None
        :param only_owner_can_change_icon_title: The only owner can change icon title.
        :type only_owner_can_change_icon_title: bool | None
        :param only_admin_can_add_member: The only admin can add member.
        :type only_admin_can_add_member: bool | None
        :param only_admin_can_call: The only admin can call.
        :type only_admin_can_call: bool | None
        :param members_can_see_private_link: The members can see private link.
        :type members_can_see_private_link: bool | None
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """

        return cast(
            Chat | None,
            await self(
                ChangeGroupSettingsMethod,
                chat_id=chat_id,
                all_can_pin_message=all_can_pin_message,
                only_owner_can_change_icon_title=only_owner_can_change_icon_title,
                only_admin_can_add_member=only_admin_can_add_member,
                only_admin_can_call=only_admin_can_call,
                members_can_see_private_link=members_can_see_private_link,
            ),
        )

    async def change_group_profile(
        self,
        chat_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> Chat | None:
        """Change group profile.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param name: The name of the chat.
        :type name: str | None
        :param description: The description of the chat.
        :type description: str | None
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """

        return cast(
            Chat | None,
            await self(
                ChangeGroupProfileMethod,
                chat_id=chat_id,
                name=name,
                description=description,
            ),
        )

    async def join_group(self, link: str) -> Chat:
        """Join group.

        :param link: Invite group link.
        :type link: str
        :returns: The resulting Chat value.
        :rtype: Chat
        """

        return cast(
            Chat,
            await self(JoinGroupMethod, link=link),
        )

    async def join_channel(self, link: str) -> Chat:
        """Join channel.

        :param link: Invite channel link.
        :type link: str
        :returns: The resulting Chat value.
        :rtype: Chat
        """

        return cast(
            Chat,
            await self(JoinChannelMethod, link=link),
        )

    async def resolve_group_by_link(self, link: str) -> Chat | None:
        """Resolve group by link.

        :param link: Invite group link.
        :type link: str
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """

        return cast(
            Chat | None,
            await self(ResolveGroupByLinkMethod, link=link),
        )

    async def revoke_invite_link(self, chat_id: int) -> Chat:
        """Revoke invite link.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :returns: The resulting Chat value.
        :rtype: Chat
        """

        return cast(
            Chat,
            await self(RevokeInviteLinkMethod, chat_id=chat_id),
        )

    async def get_chats(self, chat_ids: Iterable[int]) -> list[Chat]:
        """Retrieve chats.

        :param chat_ids: Identifiers of the chats.
        :type chat_ids: Iterable[int]
        :returns: The collection from gotten chats.
        :rtype: list[Chat]
        """

        return cast(
            list[Chat],
            await self(GetChatsMethod, chat_ids=chat_ids),
        )

    async def get_chat(self, chat_id: int) -> Chat:
        """Retrieve chat.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :returns: The resulting Chat value.
        :rtype: Chat
        :raises ValueError: If chat not found.
        """
        chats = await self.get_chats([chat_id])
        if not chats:
            raise ValueError("Chat not found")
        return chats[0]

    async def leave_group(self, chat_id: int) -> Message | None:
        """Leave group.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :returns: The resulting Message | None value.
        :rtype: Message | None
        """

        return cast(
            Message | None,
            await self(
                LeaveGroupMethod,
                chat_id=chat_id,
            ),
        )

    async def leave_channel(self, chat_id: int) -> Message | None:
        """Leave channel.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :returns: The resulting Message | None value.
        :rtype: Message | None
        """

        return cast(
            Message | None,
            await self(
                LeaveChannelMethod,
                chat_id=chat_id,
            ),
        )

    async def fetch_chats(self, marker: int | None = None) -> list[Chat]:
        """Fetch chats.

        :param marker: Pagination marker in milliseconds. If ``None``, the current time is used.
        :type marker: int | None
        :returns: The resulting Chats collection.
        :rtype: list[Chat]
        """

        return cast(
            list[Chat],
            await self(FetchChatsMethod, marker=marker),
        )

    async def get_join_requests(self, chat_id: int, count: int = 100) -> list[Member]:
        """Retrieve join requests.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param count: Maximum number of items to retrieve.
        :type count: int
        :returns: The resulting Members collection.
        :rtype: list[Member]
        """

        return cast(
            list[Member],
            await self(
                GetJoinRequestsMethod,
                chat_id=chat_id,
                count=count,
            ),
        )

    async def confirm_join_requests(
        self,
        chat_id: int,
        user_ids: Iterable[int],
        show_history: bool = True,
    ) -> Chat | None:
        """Confirm join requests.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param user_ids: Identifiers of the users.
        :type user_ids: Iterable[int]
        :param show_history: Show message history to new members.
        :type show_history: bool
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """

        return cast(
            Chat | None,
            await self(
                ConfirmJoinRequestsMethod,
                chat_id=chat_id,
                user_ids=user_ids,
                show_history=show_history,
            ),
        )

    async def confirm_join_request(
        self,
        chat_id: int,
        user_id: int,
        show_history: bool = True,
    ) -> Chat | None:
        """Confirm join request.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param user_id: Identifier of the user.
        :type user_id: int
        :param show_history: Show message history to new members.
        :type show_history: bool
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """
        return await self.confirm_join_requests(
            chat_id=chat_id,
            user_ids=[user_id],
            show_history=show_history,
        )

    async def decline_join_requests(
        self,
        chat_id: int,
        user_ids: Iterable[int],
    ) -> Chat | None:
        """Decline join requests.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param user_ids: Identifiers of the users.
        :type user_ids: Iterable[int]
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """

        return cast(
            Chat | None,
            await self(
                DeclineJoinRequestsMethod,
                chat_id=chat_id,
                user_ids=user_ids,
            ),
        )

    async def decline_join_request(
        self,
        chat_id: int,
        user_id: int,
    ) -> Chat | None:
        """Decline join request.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param user_id: Identifier of the user.
        :type user_id: int
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """
        return await self.decline_join_requests(
            chat_id=chat_id,
            user_ids=[user_id],
        )

    async def delete_chat(
        self,
        chat_id: int,
        last_event_time: int | None = None,
        for_all: bool = True,
    ) -> None:
        """Delete chat.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param last_event_time: The last event time value.
        :type last_event_time: int | None
        :param for_all: Delete only for the current account.
        :type for_all: bool
        """
        return cast(
            None,
            await self(
                DeleteChatMethod,
                chat_id=chat_id,
                last_event_time=last_event_time,
                for_all=for_all,
            ),
        )

    async def add_admin(
        self, chat_id: int, user_id: int, permissions: Iterable[ChannelPermissions]
    ) -> None:
        """Add admin.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param user_id: Identifier of the user.
        :type user_id: int
        :param permissions: Collection of permissions.
        :type permissions: Iterable[ChannelPermissions]
        """
        return cast(
            None,
            await self(
                AddAdminMethod,
                chat_id=chat_id,
                user_id=user_id,
                permissions=permissions,
            ),
        )

    async def set_channel_comments(self, chat_id: int, enabled: bool) -> None:
        """Enable or disable comments in a channel.

        :param chat_id: Channel identifier.
        :param enabled: Whether comments should be enabled.
        """
        return cast(
            None,
            await self(
                SetChannelCommentsMethod,
                chat_id=chat_id,
                enabled=enabled,
            ),
        )
