from abc import ABC, abstractmethod
from typing import Any

import pydantic
from pydantic import BaseModel

from ......models import BaseMaxObject, Message, MessageLink, EmojiReaction
from ......exceptions import MapperApiError
from ......protocol import Envelope
from ....constants import Opcode
from ...payloads.responses import PushUpdateResponse, EmojiReactionUpdateResponse
from ...payloads.models import MessageMappingModel




class TranslateModel(BaseModel, ABC):
    payload: BaseModel


    @abstractmethod
    def translate(self, context: Any) -> BaseMaxObject: pass


class PushTranslateModel(TranslateModel):
    payload: PushUpdateResponse


    def translate(self, context: Any) -> Message:
        self.payload.message.chat_id = self.payload.chat_id


        def translate_message(message: MessageMappingModel, chat_id: int | None = None) -> Message | None:
            message_link = message.link
            message.chat_id = chat_id
            for attach in message.attaches:
                if hasattr(attach, 'is_attach') and attach.is_attach:
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
                raise RuntimeError('message.id must be int')


            data: dict[str, Any] = {
                'chat_id': chat_id,
                'text': message.text,
                'message_id': message_id,
                'status': message.status,
                'time': message.time,
                'cid': message.cid,
                'type': message.type,
                'attaches': message.attaches,
                'elements': message.elements,
                'sender_id': message.sender,
            }
            if not message_link or message_link.message is None:
                try:
                    return Message.model_validate(
                        obj=data,
                        context=context,
                    )
                except pydantic.ValidationError as e:
                    return None

            msg_of_link = translate_message(message_link.message, chat_id)
            if msg_of_link:
                data['link'] = MessageLink(
                    type=message_link.type,
                    message=msg_of_link,
                )

            return Message.model_validate(
                obj=data,
                context=context,
            )

        if self.payload.message is None:
            raise RuntimeError('self.payload.message is None')

        translated_message = translate_message(self.payload.message, self.payload.chat_id)

        if translated_message is None:
            raise MapperApiError('translated_message is None (UpdateTranslate.PushTranslateModel), message: %s', self.payload.message)

        return translated_message


class EmojiReactionModel(TranslateModel):
    payload: EmojiReactionUpdateResponse


    def translate(self, context: Any) -> EmojiReaction:

        status = 'REMOVE'\
            if not (
                self.payload.reaction_info.counters or
                self.payload.reaction_info.your_reaction or
                self.payload.reaction_info.total_count
        ) else 'ADD'

        data = {
            'chat_id': self.payload.chat_id,
            'message_id': self.payload.message_id,
            'counters': self.payload.reaction_info.counters,
            'total_count': self.payload.reaction_info.total_count,
            'your_reaction': self.payload.reaction_info.your_reaction,
            'status': status,
        }

        return EmojiReaction.model_validate(
            obj=data,
            context=context,
        )


TRANSLATE_MODELS: dict[int, type[TranslateModel]] = {
    Opcode.PUSH_NOTIFICATION: PushTranslateModel,
    Opcode.MESSAGE_REACTION_UPDATE: EmojiReactionModel,
}


def translate(update: Envelope, context: Any) -> BaseMaxObject | Envelope:
    if update.opcode is None or not isinstance(update.opcode, int):
        return update

    translate_model_class = TRANSLATE_MODELS.get(update.opcode, None)
    if not translate_model_class:
        return update
    translate_model = translate_model_class(**update.model_dump())
    result: BaseMaxObject = translate_model.translate(context=context)
    return result