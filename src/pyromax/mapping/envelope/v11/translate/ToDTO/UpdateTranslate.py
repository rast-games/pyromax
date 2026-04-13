from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from src.pyromax.models import BaseMaxObject, Message, MessageLink, EmojiReaction
from src.pyromax.protocol.envelope import Envelope
from src.pyromax.mapping.envelope.constants import Opcode
from src.pyromax.mapping.envelope.v11.payloads.responses import PushUpdateResponse, EmojiReactionUpdateResponse
from src.pyromax.mapping.envelope.v11.payloads.models import MessageMappingModel




class TranslateModel(BaseModel, ABC):
    payload: BaseModel


    @abstractmethod
    def translate(self, context: Any) -> BaseMaxObject: pass


class PushTranslateModel(TranslateModel):
    payload: PushUpdateResponse


    def translate(self, context: Any) -> Message:
        self.payload.message.chat_id = self.payload.chat_id


        def translate_message(message: MessageMappingModel, chat_id: int | None = None) -> Message:
            message_link = message.link
            message.chat_id = chat_id

            raw_message_id = message.id

            message_id: int

            if type(raw_message_id) is str:
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
                return Message.model_validate(
                    obj=data,
                    context=context,
                )

            data['link'] = MessageLink(
                type=message_link.type,
                message=translate_message(message_link.message, chat_id),
            ).model_dump()

            return Message.model_validate(
                obj=data,
                context=context,
            )

        if self.payload.message is None:
            raise RuntimeError('self.payload.message is None')

        return translate_message(self.payload.message, self.payload.chat_id)


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