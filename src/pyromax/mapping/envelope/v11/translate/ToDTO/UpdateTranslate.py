from abc import ABC, abstractmethod
from typing import Any, cast

import pydantic
from pydantic import BaseModel

from ......models import (
    BaseMaxObject,
    Chat,
    EmojiReaction,
    Message,
    MessageDeleteEvent,
    MessageLink,
    MessageReadEvent,
    Presence,
    PresenceEvent,
    TypingEvent,
)
from ......exceptions import MapperApiError
from ......protocol import Envelope
from ....constants import Cmd, Opcode
from ...payloads.responses import PushUpdateResponse, EmojiReactionUpdateResponse
from ...payloads.models import (
    ChatMappingModel,
    MessageMappingModel,
    PresenceMappingModel,
)
from .ModelsTranslate import translate_models


class TranslateModel(BaseModel, ABC):
    payload: BaseModel | dict[str, Any]

    @abstractmethod
    def translate(self, context: Any) -> BaseMaxObject:
        """Translate translate between mapping and public models.

        :param context: Runtime context used while processing the request.
        :type context: Any
        :returns: The translated BaseMaxObject instance.
        :rtype: BaseMaxObject
        """
        pass


class PushTranslateModel(TranslateModel):
    payload: PushUpdateResponse

    def translate(self, context: Any) -> Message | MessageDeleteEvent:
        """Translate the mapping payload into Message.

        :param context: Runtime context used while processing the request.
        :type context: Any
        :returns: The resulting Message value.
        :rtype: Message
        :raises RuntimeError: If self.payload.message is None.
        :raises MapperApiError: If translated_message is None (UpdateTranslate.PushTranslateModel), message: %s.
        :raises RuntimeError: If message.id must be int.
        """
        self.payload.message.chat_id = self.payload.chat_id

        def translate_message(
            message: MessageMappingModel, chat_id: int | None = None
        ) -> Message | None:
            """Translate message.

            :param message: MessageMappingModel instance to process.
            :type message: MessageMappingModel
            :param chat_id: Identifier of the chat.
            :type chat_id: int | None
            :returns: The resulting Message | None value.
            :rtype: Message | None
            :raises RuntimeError: If message.id must be int.
            """
            message_link = message.link
            message.chat_id = chat_id
            for attach in message.attaches:
                if hasattr(attach, "is_attach") and attach.is_attach:
                    attach.uploaded = True
                    attach.chat_id = chat_id
                    attach.message_id = message.id

            raw_message_id = message.id

            message_id: int
            if type(raw_message_id) is int:
                message_id = raw_message_id
            elif type(raw_message_id) is str:
                message_id = int(raw_message_id)
            else:
                raise RuntimeError("message.id must be int")

            data: dict[str, Any] = {
                "chat_id": chat_id,
                "text": message.text,
                "message_id": message_id,
                "status": message.status,
                "time": message.time,
                "cid": message.cid,
                "type": message.type,
                "attaches": message.attaches,
                "elements": message.elements,
                "sender_id": message.sender,
            }
            if not message_link or message_link.message is None:
                try:
                    return Message.model_validate(
                        obj=data,
                        context=context,
                    )
                except pydantic.ValidationError:
                    return None

            msg_of_link = translate_message(message_link.message, chat_id)
            if msg_of_link:
                data["link"] = MessageLink(
                    type=message_link.type,
                    message=msg_of_link,
                )

            return Message.model_validate(
                obj=data,
                context=context,
            )

        if self.payload.message is None:
            raise RuntimeError("self.payload.message is None")

        translated_message = translate_message(
            self.payload.message, self.payload.chat_id
        )

        if translated_message is None:
            raise MapperApiError(
                "translated_message is None (UpdateTranslate.PushTranslateModel), message: %s",
                self.payload.message,
            )

        if translated_message.status == "REMOVED":
            return MessageDeleteEvent(
                message=translated_message,
                chat_id=translated_message.chat_id,
                message_ids=[translated_message.message_id],
            )

        return translated_message


class EmojiReactionModel(TranslateModel):
    payload: EmojiReactionUpdateResponse

    def translate(self, context: Any) -> EmojiReaction:
        """Translate the mapping payload into EmojiReaction.

        :param context: Runtime context used while processing the request.
        :type context: Any
        :returns: The resulting EmojiReaction value.
        :rtype: EmojiReaction
        """
        status = (
            "REMOVE"
            if not (
                self.payload.reaction_info.counters
                or self.payload.reaction_info.your_reaction
                or self.payload.reaction_info.total_count
            )
            else "ADD"
        )

        data = {
            "chat_id": self.payload.chat_id,
            "message_id": str(self.payload.message_id),
            "counters": self.payload.reaction_info.counters,
            "total_count": self.payload.reaction_info.total_count,
            "your_reaction": self.payload.reaction_info.your_reaction,
            "status": status,
        }

        return EmojiReaction.model_validate(
            obj=data,
            context=context,
        )


class AggregateReactionModel(TranslateModel):
    payload: dict[str, Any]

    def translate(self, context: Any) -> EmojiReaction:
        payload = self.payload
        reaction_info = payload.get("reactionInfo", payload)
        return EmojiReaction.model_validate(
            {
                "chat_id": payload.get("chatId", payload.get("chat_id")),
                "message_id": payload.get("messageId", payload.get("message_id")),
                "counters": reaction_info.get("counters"),
                "total_count": reaction_info.get(
                    "totalCount", reaction_info.get("total_count")
                ),
                "your_reaction": reaction_info.get(
                    "yourReaction", reaction_info.get("your_reaction")
                ),
                "status": "ADD",
            },
            context=context,
        )


class MessageTranslateModel(TranslateModel):
    payload: dict[str, Any]

    def translate(self, context: Any) -> Message | MessageDeleteEvent:
        if "message" in self.payload:
            return PushTranslateModel.model_validate(
                {"payload": self.payload}
            ).translate(context)

        mapping_message = MessageMappingModel.model_validate(self.payload)
        mapping_message.status = "EDITED"
        message = cast(Message, translate_models(mapping_message))
        message.as_(context.get("max_api") if context else None)
        return message


class MessageReadTranslateModel(TranslateModel):
    payload: dict[str, Any]

    def translate(self, context: Any) -> MessageReadEvent:
        return MessageReadEvent.model_validate(
            {
                "set_as_unread": self.payload["setAsUnread"],
                "chat_id": self.payload["chatId"],
                "user_id": self.payload["userId"],
                "mark": self.payload["mark"],
            },
            context=context,
        )


class TypingTranslateModel(TranslateModel):
    payload: dict[str, Any]

    def translate(self, context: Any) -> TypingEvent:
        return TypingEvent.model_validate(
            {
                "chat_id": self.payload["chatId"],
                "user_id": self.payload["userId"],
            },
            context=context,
        )


class PresenceTranslateModel(TranslateModel):
    payload: dict[str, Any]

    def translate(self, context: Any) -> PresenceEvent:
        presence = cast(
            Presence,
            translate_models(
                PresenceMappingModel.model_validate(self.payload["presence"])
            ),
        )
        return PresenceEvent.model_validate(
            {
                "presence": presence,
                "user_id": self.payload["userId"],
            },
            context=context,
        )


class MessageDeleteTranslateModel(TranslateModel):
    payload: dict[str, Any]

    def translate(self, context: Any) -> MessageDeleteEvent:
        chat = None
        chat_payload = self.payload.get("chat")
        if chat_payload is not None:
            chat = cast(
                Chat,
                translate_models(ChatMappingModel.model_validate(chat_payload)),
            )
            chat.as_(context.get("max_api") if context else None)

        chat_id = self.payload.get("chatId")
        if chat_id is None and chat is not None:
            chat_id = chat.id

        return MessageDeleteEvent.model_validate(
            {
                "message_ids": self.payload["messageIds"],
                "chat_id": chat_id,
                "chat": chat,
                "ttl": self.payload.get("ttl", False),
            },
            context=context,
        )


class ChatUpdateTranslateModel(TranslateModel):
    payload: dict[str, Any]

    def translate(self, context: Any) -> Chat:
        chat_payload = self.payload.get("chat", self.payload)
        chat = cast(
            Chat,
            translate_models(ChatMappingModel.model_validate(chat_payload)),
        )
        chat.as_(context.get("max_api") if context else None)
        return chat


TRANSLATE_MODELS: dict[int, type[TranslateModel]] = {
    Opcode.PUSH_NOTIFICATION: PushTranslateModel,
    Opcode.EDIT_MESSAGE: MessageTranslateModel,
    Opcode.TYPING_NOTIFICATION: TypingTranslateModel,
    Opcode.MESSAGE_READ_NOTIFICATION: MessageReadTranslateModel,
    Opcode.PRESENCE_NOTIFICATION: PresenceTranslateModel,
    Opcode.CHAT_NOTIFICATION: ChatUpdateTranslateModel,
    Opcode.MESSAGE_DELETE_NOTIFICATION: MessageDeleteTranslateModel,
    Opcode.MESSAGE_REACTIONS_CHANGED: AggregateReactionModel,
    Opcode.MESSAGE_REACTION_UPDATE: EmojiReactionModel,
}


def translate(update: Envelope, context: Any) -> BaseMaxObject | Envelope:
    """Translate the mapping payload into BaseMaxObject | Envelope.

    :param update: Incoming update to process.
    :type update: Envelope
    :param context: Runtime context used while processing the request.
    :type context: Any
    :returns: The envelope populated with the request opcode and payload.
    :rtype: BaseMaxObject | Envelope
    """
    if (
        update.cmd != Cmd.REQUEST
        or update.opcode is None
        or not isinstance(update.opcode, int)
    ):
        return update

    translate_model_class = TRANSLATE_MODELS.get(update.opcode, None)
    if not translate_model_class:
        return update
    translate_model = translate_model_class(**update.model_dump())
    result: BaseMaxObject = translate_model.translate(context=context)
    return result
