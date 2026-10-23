import time
from typing import cast, Literal

from .base import BaseMethod, Envelope, Cmd, Opcode, VERSION
from ...payloads.requests import (
    CreateChatRequest,
    ChatMemberOperationRequest,
    ChangeGroupSettingsRequest,
    ChangeGroupProfileRequest,
    LinkGroupRequest,
    RevokePrivateLinkRequest,
    GetChatInfoRequest,
    LeaveChatRequest,
    FetchChatsRequest,
    FetchJoinRequestsRequest,
    DeleteChatRequest,
    AddAdminRequest,
    SetChannelCommentsRequest,
    BlockCommentAuthorRequest,
)
from ...payloads.models import (
    CreateGroupMessageMappingModel,
    CreateGroupAttachMappingModel,
    ChangeGroupSettingsMappingModel,
    ChannelCommentsMappingModel,
)


class CreateChatMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the create chat protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.SEND_MESSAGE
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = CreateChatRequest(
            notify=self.args.get("notify", True),
            message=CreateGroupMessageMappingModel(
                cid=self.args["cid"],
                attaches=[
                    CreateGroupAttachMappingModel(
                        type=cast(Literal["CONTROL"], self.args.get("type", "CONTROL")),
                        event=cast(Literal["new"], self.args.get("event", "new")),
                        chat_type=cast(
                            Literal["CHAT", "DIALOG", "CHANNEL"],
                            self.args.get("chat_type", "CHAT"),
                        ),
                        title=self.args["title"],
                        user_ids=self.args.get("user_ids", []),
                    ),
                ],
            ),
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class ChatMemberOperationMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the chat member operation protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.OPERATION_WITH_CHAT_MEMBER
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = ChatMemberOperationRequest(
            chat_id=self.args["chat_id"],
            user_ids=self.args["user_ids"],
            show_history=self.args.get("show_history"),
            operation=self.args["operation"],
            clean_msg_period=self.args.get("clean_msg_period"),
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class ChangeGroupSettingsMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the change group settings protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.CHAT_UPDATE
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = ChangeGroupSettingsRequest(
            chat_id=self.args["chat_id"],
            options=ChangeGroupSettingsMappingModel(
                only_owner_can_change_icon_title=self.args.get(
                    "only_owner_can_change_icon_title"
                ),
                all_can_pin_message=self.args.get("all_can_pin_message"),
                only_admin_can_add_member=self.args.get("only_admin_can_add_member"),
                only_admin_can_call=self.args.get("only_admin_can_call"),
                members_can_see_private_link=self.args.get(
                    "members_can_see_private_link"
                ),
            ),
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class SetChannelCommentsMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.CHAT_UPDATE
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = SetChannelCommentsRequest(
            chat_id=self.args["chat_id"],
            options=ChannelCommentsMappingModel(
                comments=self.args["enabled"],
            ),
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class BlockCommentAuthorMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request.opcode = Opcode.OPERATION_WITH_CHAT_MEMBER
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = BlockCommentAuthorRequest(
            chat_id=self.args["chat_id"],
            post_id=self.args["post_id"],
            user_ids=self.args["user_ids"],
            message_id=self.args["message_id"],
            clean_msg_period=self.args["clean_msg_period"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class ChangeGroupProfileMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the change group profile protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.CHAT_UPDATE
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = ChangeGroupProfileRequest(
            chat_id=self.args["chat_id"],
            theme=self.args.get("name"),
            description=self.args.get("description"),
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class JoinGroupMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the join group protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.JOIN_GROUP
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = LinkGroupRequest(
            link=self.args["link"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class ResolveGroupByLinkMethod(JoinGroupMethod):
    circuit_breaker_retry_safe = True

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the resolve group by link protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request = await super().__call__(request)
        request.opcode = Opcode.LINK_INFO
        return request


class RevokePrivateLinkMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the revoke private link protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.CHAT_UPDATE
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = RevokePrivateLinkRequest(
            revoke_private_link=self.args.get("rework_invite_link", True),
            chat_id=self.args["chat_id"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class GetChatInfoMethod(BaseMethod):
    circuit_breaker_retry_safe = True

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the get chat info protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.GET_CHAT
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = GetChatInfoRequest(
            chat_ids=self.args["chat_ids"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class LeaveChatMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the leave chat protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.LEAVE_CHAT
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = LeaveChatRequest(
            chat_id=self.args["chat_id"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class FetchChatsMethod(BaseMethod):
    circuit_breaker_retry_safe = True

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the fetch chats protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.FETCH_CHATS
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = FetchChatsRequest(
            marker=self.args.get("marker") or int(time.time() * 1000),
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class FetchJoinRequestsMethod(BaseMethod):
    circuit_breaker_retry_safe = True

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the fetch join requests protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.CHAT_MEMBERS
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = FetchJoinRequestsRequest(
            chat_id=self.args["chat_id"],
            count=self.args["count"],
            type=self.args.get("type") or "JOIN_REQUEST",
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class DeleteChatMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the delete chat protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.DELETE_CHAT
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = DeleteChatRequest(
            chat_id=self.args["chat_id"],
            last_event_time=self.args["last_event_time"],
            for_all=self.args.get("for_all") or True,
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class AddAdminMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the add admin protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.OPERATION_WITH_CHAT_MEMBER
        request.cmd = Cmd.REQUEST
        request.ver = self.VERSION
        request.payload = AddAdminRequest(
            chat_id=self.args["chat_id"],
            user_ids=self.args["user_ids"],
            permissions=self.args["permissions"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


__all__ = [
    "CreateChatMethod",
    "ChatMemberOperationMethod",
    "ChangeGroupSettingsMethod",
    "SetChannelCommentsMethod",
    "BlockCommentAuthorMethod",
    "ChangeGroupProfileMethod",
    "JoinGroupMethod",
    "ResolveGroupByLinkMethod",
    "RevokePrivateLinkMethod",
    "GetChatInfoMethod",
    "LeaveChatMethod",
    "FetchChatsMethod",
    "FetchJoinRequestsMethod",
    "DeleteChatMethod",
    "AddAdminMethod",
]
