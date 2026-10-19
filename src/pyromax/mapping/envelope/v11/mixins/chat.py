import time
from typing import cast
from collections.abc import Iterable
from functools import reduce
from operator import or_

from .MixinProtocol import MixinProtocol, T_CHAT
from .....exceptions import MapperApiError
from .....models import Chat, Message, Member, ChannelPermissions
from ..methods.immutable import (
    CreateChatMethod,
    ChatMemberOperationMethod,
    ChangeGroupSettingsMethod,
    ChangeGroupProfileMethod,
    JoinGroupMethod,
    ResolveGroupByLinkMethod,
    RevokePrivateLinkMethod,
    GetChatInfoMethod,
    LeaveChatMethod,
    FetchChatsMethod,
    FetchJoinRequestsMethod,
    DeleteChatMethod,
    AddAdminMethod,
    SetChannelCommentsMethod as SetChannelCommentsProtocolMethod,
)
from ..payloads.responses import (
    CreateGroupResponse,
    ChatContainsResponse,
    ChatsContainsResponse,
    MessageContainsResponse,
    MembersContainsResponse,
)
from ..translate.ToDTO import translate_models
from ..translate.FromDTO import reverse_translate_channel_permissions


class ChatMixin(MixinProtocol):
    def _cache_chat(self, chat: T_CHAT) -> T_CHAT:
        """Cache chat.

        :param chat: Chat instance to process.
        :type chat: Chat
        :returns: The resulting Chat value.
        :rtype: Chat
        :raises RuntimeError: If mapper not bound to max_api instance.
        """
        chat = self.bind_api_instance(chat)
        if self.max_api is None:
            raise RuntimeError("Mapper not bound to max_api instance")

        if self.max_api.chats is None:
            self.max_api.chats = [chat]
            return chat

        for inx, cached in enumerate(self.max_api.chats):
            if cached.id == chat.id:
                self.max_api.chats[inx] = chat
                return chat

        self.max_api.chats.append(chat)
        return chat

    def _get_cached_chat(self, chat_id: int) -> Chat | None:
        """Retrieve cached chat.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        :raises RuntimeError: If mapper not bound to max_api instance.
        """
        if self.max_api is None:
            raise RuntimeError("Mapper not bound to max_api instance")

        for chat in self.max_api.chats or []:
            if chat.id == chat_id:
                return chat
        return None

    def _remove_cached_chat(self, chat_id: int) -> None:
        """Remove cached chat.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :raises RuntimeError: If mapper not bound to max_api instance.
        """
        if self.max_api is None:
            raise RuntimeError("Mapper not bound to max_api instance")

        if self.max_api.chats is None:
            return

        self.max_api.chats = [chat for chat in self.max_api.chats if chat.id != chat_id]

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
        if participant_ids is None:
            participant_ids = []
        response = await self.send(
            method=CreateChatMethod(
                title=title,
                user_ids=participant_ids,
                notify=notify,
                chat_type=chat_type,
                event=event,
                type=typeof,
                cid=self._next_cid(),
            )
        )
        chat_and_message = CreateGroupResponse(**response.payload)
        if chat_and_message.chat is None:
            return None, None

        mapped_create_chat_message = chat_and_message.message
        mapped_chat = chat_and_message.chat
        for attach in mapped_create_chat_message.attaches:
            attach.chat_id = chat_and_message.chat_id
            attach.message_id = mapped_create_chat_message.id

        mapped_create_chat_message.chat_id = chat_and_message.chat_id

        message = cast(Message, translate_models(mapped_create_chat_message))
        chat = cast(Chat, translate_models(mapped_chat))
        return self._cache_chat(chat), self.bind_api_instance(message)

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
        :param show_history: The show history value.
        :type show_history: bool
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """
        response = await self.send(
            method=ChatMemberOperationMethod(
                chat_id=chat_id,
                user_ids=user_ids,
                show_history=show_history,
                operation="add",
            )
        )

        mapped_chat = ChatContainsResponse(**response.payload).chat
        if mapped_chat is None:
            return None

        chat = cast(Chat, translate_models(mapped_chat))
        return self._cache_chat(chat)

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
        :param clean_msg_period: The clean msg period value.
        :type clean_msg_period: int
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """
        response = await self.send(
            method=ChatMemberOperationMethod(
                chat_id=chat_id,
                user_ids=user_ids,
                clean_msg_period=clean_msg_period,
                operation="remove",
            )
        )

        mapped_chat = ChatContainsResponse(**response.payload).chat
        if mapped_chat is None:
            return None

        chat = cast(Chat, translate_models(mapped_chat))
        return self._cache_chat(chat)

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
        :param all_can_pin_message: The all can pin message value.
        :type all_can_pin_message: bool | None
        :param only_owner_can_change_icon_title: The only owner can change icon title value.
        :type only_owner_can_change_icon_title: bool | None
        :param only_admin_can_add_member: The only admin can add member value.
        :type only_admin_can_add_member: bool | None
        :param only_admin_can_call: The only admin can call value.
        :type only_admin_can_call: bool | None
        :param members_can_see_private_link: The members can see private link value.
        :type members_can_see_private_link: bool | None
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """
        response = await self.send(
            method=ChangeGroupSettingsMethod(
                chat_id=chat_id,
                all_can_pin_message=all_can_pin_message,
                only_owner_can_change_icon_title=only_owner_can_change_icon_title,
                only_admin_can_add_member=only_admin_can_add_member,
                only_admin_can_call=only_admin_can_call,
                members_can_see_private_link=members_can_see_private_link,
            )
        )

        mapped_chat = ChatContainsResponse(**response.payload).chat
        if mapped_chat is None:
            return None

        chat = cast(Chat, translate_models(mapped_chat))
        return self._cache_chat(chat)

    async def set_channel_comments(self, chat_id: int, enabled: bool) -> None:
        """Enable or disable comments in a channel."""
        response = await self.send(
            method=SetChannelCommentsProtocolMethod(
                chat_id=chat_id,
                enabled=enabled,
            ),
            check_errors=True,
        )
        mapped_chat = ChatContainsResponse(**response.payload).chat
        if mapped_chat is not None:
            chat = cast(Chat, translate_models(mapped_chat))
            self._cache_chat(chat)

    async def change_group_profile(
        self,
        chat_id: int,
        name: str | None = None,
        description: str | None = None,
    ) -> Chat | None:
        """Change group profile.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param name: The name value.
        :type name: str | None
        :param description: The description value.
        :type description: str | None
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """
        response = await self.send(
            method=ChangeGroupProfileMethod(
                chat_id=chat_id,
                name=name,
                description=description,
            )
        )
        mapped_chat = ChatContainsResponse(**response.payload).chat
        if mapped_chat is None:
            return None

        chat = cast(Chat, translate_models(mapped_chat))
        return self._cache_chat(chat)

    async def _join_chat(self, link: str) -> Chat:
        """Join chat.

        :param link: Invite, message, or resource link.
        :type link: str
        :returns: The resulting Chat value.
        :rtype: Chat
        :raises MapperApiError: If joinGroup request doesn't return a chat.
        """
        response = await self.send(method=JoinGroupMethod(link=link))
        mapped_chat = ChatContainsResponse(**response.payload).chat
        if mapped_chat is None:
            raise MapperApiError("JoinGroup request doesn't return a chat")
        chat = cast(Chat, translate_models(mapped_chat))
        return self._cache_chat(chat)

    @staticmethod
    def _prepare_chat_join_link(link: str) -> str | None:
        """Prepare chat join link.

        :param link: Invite, message, or resource link.
        :type link: str
        :returns: The resulting str | None value.
        :rtype: str | None
        """
        idx = link.find("join/")
        return link[idx:] if idx != -1 else None

    async def join_group(self, link: str) -> Chat:
        """Join group.

        :param link: Invite, message, or resource link.
        :type link: str
        :returns: The resulting Chat value.
        :rtype: Chat
        :raises ValueError: If join link invalid.
        """
        parsed_link = self._prepare_chat_join_link(link)
        if parsed_link is None:
            raise ValueError("Join link invalid")
        return await self._join_chat(parsed_link)

    async def join_channel(self, link: str) -> Chat:
        """Join channel.

        :param link: Invite, message, or resource link.
        :type link: str
        :returns: The resulting Chat value.
        :rtype: Chat
        """
        parsed_link = self._prepare_chat_join_link(link)

        return await self._join_chat(parsed_link or link)

    async def resolve_group_by_link(self, link: str) -> Chat | None:
        """Resolve group by link.

        :param link: Invite, message, or resource link.
        :type link: str
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        :raises ValueError: If invalid group link.
        """
        parsed_link = self._prepare_chat_join_link(link)
        if parsed_link is None:
            raise ValueError("Invalid group link")

        response = await self.send(
            method=ResolveGroupByLinkMethod(
                link=parsed_link,
            )
        )
        mapped_chat = ChatContainsResponse(**response.payload).chat
        if mapped_chat is None:
            return None
        chat = cast(Chat, translate_models(mapped_chat))
        return self._cache_chat(chat)

    async def revoke_invite_link(self, chat_id: int) -> Chat:
        """Revoke invite link.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :returns: The resulting Chat value.
        :rtype: Chat
        :raises MapperApiError: If rework invite link request doesn't return a chat.
        """
        response = await self.send(
            method=RevokePrivateLinkMethod(
                chat_id=chat_id,
                rework_private_link=True,
            )
        )

        mapped_chat = ChatContainsResponse(**response.payload).chat
        if mapped_chat is None:
            raise MapperApiError("rework invite link request doesn't return a chat")
        chat = cast(Chat, translate_models(mapped_chat))
        return self._cache_chat(chat)

    async def get_chats(self, chat_ids: Iterable[int]) -> list[Chat]:
        """Retrieve chats.

        :param chat_ids: Identifiers of the chats.
        :type chat_ids: Iterable[int]
        :returns: The resulting collection.
        :rtype: list[Chat]
        """
        cached = {
            chat_id: chat
            for chat_id in chat_ids
            if (chat := self._get_cached_chat(chat_id)) is not None
        }
        missed_chat_ids = [chat_id for chat_id in chat_ids if chat_id not in cached]

        if missed_chat_ids:
            response = await self.send(
                method=GetChatInfoMethod(
                    chat_ids=missed_chat_ids,
                )
            )
            mapped_chats = ChatsContainsResponse(**response.payload).chats or []
            for mapped_chat in mapped_chats:
                chat = cast(Chat, translate_models(mapped_chat))
                chat = self._cache_chat(chat)
                cached[chat.id] = chat

        return [cached[chat_id] for chat_id in chat_ids if chat_id in cached]

    async def leave_group(self, chat_id: int) -> Message | None:
        """Leave group.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :returns: The resulting Message | None value.
        :rtype: Message | None
        """
        response = await self.send(
            method=LeaveChatMethod(
                chat_id=chat_id,
            )
        )

        msg = MessageContainsResponse(**response.payload).message
        if msg is None:
            return None
        msg.chat_id = chat_id

        self._remove_cached_chat(chat_id)
        return self.bind_api_instance(cast(Message, translate_models(msg)))

    async def leave_channel(self, chat_id: int) -> Message | None:
        """Leave channel.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :returns: The resulting Message | None value.
        :rtype: Message | None
        """
        return await self.leave_group(chat_id)

    async def fetch_chats(self, marker: int | None = None) -> list[Chat]:
        """Fetch chats.

        :param marker: Pagination marker from which to continue.
        :type marker: int | None
        :returns: The resulting collection.
        :rtype: list[Chat]
        """
        response = await self.send(
            method=FetchChatsMethod(
                marker=marker or int(time.time() * 1000),
            )
        )

        mapped_chats = ChatsContainsResponse(**response.payload).chats or []
        chats = [
            self._cache_chat(cast(Chat, translate_models(chat)))
            for chat in mapped_chats
        ]

        return chats

    async def get_join_requests(self, chat_id: int, count: int = 100) -> list[Member]:
        """Retrieve join requests.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param count: Maximum number of items to retrieve.
        :type count: int
        :returns: The resulting collection.
        :rtype: list[Member]
        """
        response = await self.send(
            method=FetchJoinRequestsMethod(
                chat_id=chat_id,
                count=count,
            )
        )

        mapped_members = MembersContainsResponse(**response.payload).members or []
        return [
            self.bind_api_instance(cast(Member, translate_models(member)))
            for member in mapped_members
        ]

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
        :param show_history: The show history value.
        :type show_history: bool
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """
        response = await self.send(
            method=ChatMemberOperationMethod(
                chat_id=chat_id,
                user_ids=user_ids,
                show_history=show_history,
                operation="add",
            )
        )
        mapped_chat = ChatContainsResponse(**response.payload)
        if mapped_chat is None:
            return None
        chat = cast(Chat, translate_models(mapped_chat))
        return self._cache_chat(chat)

    async def decline_join_requests(
        self, chat_id: int, user_ids: Iterable[int]
    ) -> Chat | None:
        """Decline join requests.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param user_ids: Identifiers of the users.
        :type user_ids: Iterable[int]
        :returns: The resulting Chat | None value.
        :rtype: Chat | None
        """
        response = await self.send(
            method=ChatMemberOperationMethod(
                chat_id=chat_id,
                user_ids=user_ids,
                operation="remove",
            )
        )
        mapped_chat = ChatContainsResponse(**response.payload).chat
        if mapped_chat is None:
            return None

        chat = cast(Chat, translate_models(mapped_chat))
        return self._cache_chat(chat)

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
        :param for_all: The for all value.
        :type for_all: bool
        """
        await self.send(
            method=DeleteChatMethod(
                chat_id=chat_id,
                last_event_time=last_event_time or int(time.time() * 1000),
                for_all=for_all,
            )
        )

        return None

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
        mapped_channel_permissions = [
            reverse_translate_channel_permissions(permission)
            for permission in permissions
        ]

        await self.send(
            method=AddAdminMethod(
                chat_id=chat_id,
                user_ids=[user_id],
                permissions=reduce(or_, mapped_channel_permissions),
            )
        )
        return None
