from datetime import datetime, timedelta
from typing import cast, Literal

from .base import BaseMethod, Envelope, Cmd, Opcode, VERSION
from ...payloads.requests import (
    SendMessageRequest,
    GetMessagesRequest,
    EditMessageRequest,
    GetChatHistoryRequest,
    DeleteMessageRequest,
    PinMessageRequest,
    AddReactionRequest,
    RemoveReactionRequest,
    GetReactionsRequest,
    ReactionInfoRequest,
    ReadMessageRequest,
    VotePollRequest,
    SendCommentRequest,
    EditCommentRequest,
    CommentsHistoryRequest,
    DeleteCommentRequest,
    AddCommentReactionRequest,
)
from ...translate.FromDTO import reverse_translate_message
from ...payloads.models import (
    DelayedAttributesMappingModel,
    MessageMappingModel,
    MessageLinkMappingModel,
)


def _convert_send_at(send_at: datetime | timedelta | int) -> int:
    if isinstance(send_at, datetime):
        return int(send_at.timestamp() * 1000)
    if isinstance(send_at, timedelta):
        return int((datetime.now() + send_at).timestamp() * 1000)
    return send_at * 1000


class SendMessageMethod(BaseMethod):
    # Reusing the same method instance preserves CID, which lets MAX
    # deduplicate a request when its response was lost in transit.
    circuit_breaker_retry_safe = True

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the send message protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.SEND_MESSAGE
        request.cmd = Cmd.REQUEST
        request.ver = VERSION

        notify = self.args.get("notify")
        send_at = self.args.get("send_at")

        main_link = self.args.get("link")
        request.payload = SendMessageRequest(
            chat_id=self.args["chat_id"],
            message=MessageMappingModel(
                text=self.args.get("text"),
                cid=self.args["cid"],
                attaches=[],
                elements=(
                    self.args["elements"]
                    if self.args["text"] and self.args["elements"]
                    else None
                ),
                link=(
                    MessageLinkMappingModel(
                        type=main_link.type,
                        message_id=main_link.message_id,
                        chat_id=main_link.chat_id,
                        message=reverse_translate_message(main_link.message),
                    )
                    if main_link
                    else None
                ),
                delayed_attributes=(
                    DelayedAttributesMappingModel(
                        time_to_fire=_convert_send_at(send_at),
                        notify_sender=notify if notify is not None else True,
                    )
                    if send_at
                    else None
                ),
            ),
            notify=notify if notify is not None else True,
        )

        request.payload.message.attaches = (
            self.args["attaches"] if self.args["attaches"] else []
        )
        request.payload = request.payload.model_dump(by_alias=True, exclude_none=True)

        return request


class SendCommentMethod(SendMessageMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request = await super().__call__(request)
        request.payload = SendCommentRequest.model_validate(
            {**request.payload, "postId": self.args["post_id"]}
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class EditMessageMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the edit message protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.EDIT_MESSAGE
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = EditMessageRequest(
            chat_id=self.args["chat_id"],
            message_id=self.args["message_id"],
            text=self.args.get("text"),
            elements=(
                self.args["elements"]
                if self.args["text"] and self.args["elements"]
                else None
            ),
            attachments=self.args["attaches"] if self.args["attaches"] else [],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class EditCommentMethod(EditMessageMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request = await super().__call__(request)
        request.payload = EditCommentRequest.model_validate(
            {**request.payload, "postId": self.args["post_id"]}
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class GetMessagesMethod(BaseMethod):
    circuit_breaker_retry_safe = True

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the get messages protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.GET_MESSAGES
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = GetMessagesRequest(
            message_ids=self.args["message_ids"],
            chat_id=self.args["chat_id"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class GetChatHistoryMethod(BaseMethod):
    circuit_breaker_retry_safe = True

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the get chat history protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.GET_CHAT_MESSAGES_PER_CHUNK
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = GetChatHistoryRequest(
            chat_id=self.args["chat_id"],
            from_=self.args["from_time"],
            forward=self.args["forward"],
            backward=self.args["backward"],
            backward_time=self.args["backward_time"],
            forward_time=self.args["forward_time"],
            item_type=self.args["item_type"],
            get_messages=self.args["get_messages"],
            get_chat=self.args["get_chat"],
            interactive=self.args["interactive"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class FetchCommentsMethod(GetChatHistoryMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request = await super().__call__(request)
        request.payload = CommentsHistoryRequest.model_validate(
            {**request.payload, "postId": self.args["post_id"]}
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class DeleteMessageMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the delete message protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.DELETE_MESSAGE
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = DeleteMessageRequest(
            chat_id=self.args["chat_id"],
            message_ids=self.args["message_ids"],
            for_me=cast(bool, self.args.get("for_me")),
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class DeleteCommentMethod(DeleteMessageMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request = await super().__call__(request)
        request.payload = DeleteCommentRequest.model_validate(
            {**request.payload, "postId": self.args["post_id"]}
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class PinMessageMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the pin message protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.CHAT_UPDATE
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = PinMessageRequest(
            chat_id=self.args["chat_id"],
            notify_pin=self.args["notify_pin"],
            pin_message_id=self.args["pin_message_id"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class AddReactionMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the add reaction protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.ADD_REACTION
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = AddReactionRequest(
            chat_id=self.args["chat_id"],
            message_id=self.args["message_id"],
            reaction=ReactionInfoRequest(
                reaction_type=self.args.get("reaction_type", "EMOJI"),
                id=self.args["reaction_id"],
            ),
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class AddCommentReactionMethod(AddReactionMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        request = await super().__call__(request)
        request.payload = AddCommentReactionRequest.model_validate(
            {**request.payload, "postId": self.args["post_id"]}
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class RemoveReactionMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the remove reaction protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.REMOVE_REACTION
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = RemoveReactionRequest(
            chat_id=self.args["chat_id"],
            message_id=self.args["message_id"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class GetReactionsMethod(BaseMethod):
    circuit_breaker_retry_safe = True

    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the get reactions protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.GET_REACTIONS
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = GetReactionsRequest(
            chat_id=self.args["chat_id"],
            message_ids=self.args["message_ids"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class ReadMessageMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the read message protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.READ_MESSAGE
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = ReadMessageRequest(
            type=cast(Literal["READ_MESSAGE", "READ_REACTION"], self.args["type"]),
            chat_id=self.args["chat_id"],
            message_id=self.args["message_id"],
            mark=self.args["mark"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


class VotePollMethod(BaseMethod):
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the vote poll protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        request.opcode = Opcode.VOTE_POLL
        request.cmd = Cmd.REQUEST
        request.ver = VERSION
        request.payload = VotePollRequest(
            chat_id=self.args["chat_id"],
            message_id=self.args["message_id"],
            poll_id=self.args["poll_id"],
            answers_ids=self.args["answer_ids"],
        ).model_dump(by_alias=True, exclude_none=True)
        return request


__all__ = [
    "SendMessageMethod",
    "SendCommentMethod",
    "EditMessageMethod",
    "EditCommentMethod",
    "GetMessagesMethod",
    "GetChatHistoryMethod",
    "FetchCommentsMethod",
    "DeleteMessageMethod",
    "DeleteCommentMethod",
    "PinMessageMethod",
    "AddReactionMethod",
    "AddCommentReactionMethod",
    "RemoveReactionMethod",
    "GetReactionsMethod",
    "ReadMessageMethod",
    "VotePollMethod",
]
