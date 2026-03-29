from abc import ABC, abstractmethod
from pyexpat import model
from typing import ClassVar

from src.pyromax.models import BaseMaxObject, Message, EmojiReaction, VideoAttachment, FileAttachment, PhotoAttachment
from src.pyromax.protocol.envelope import Envelope
from .constants import Opcode, Cmd
from .payloads import PushPayloadModel, EmojiReactionUpdateModel, File, BaseFile, Photo, Video

from pydantic import BaseModel


class TranslateModel(BaseModel, ABC):
    # opcode: ClassVar[Opcode]
    # Cmd: ClassVar[Cmd]
    payload: dict

    @abstractmethod
    def translate(self) -> BaseMaxObject: pass


class PushTranslateModel(TranslateModel):
    # opcode = Opcode.PUSH_NOTIFICATION
    # Cmd = Cmd.REQUEST
    payload: PushPayloadModel

    def translate(self) -> Message:
        return Message(
            chat_id=self.payload.chat_id,
            text=self.payload.message.text,
            message_id=self.payload.message.id,
            status=self.payload.message.status,
            time=self.payload.message.time,
            cid=self.payload.message.cid,
            type=self.payload.message.type,
            attaches=self.payload.message.attaches,
        )


class EmojiReactionModel(TranslateModel):
    payload: EmojiReactionUpdateModel

    def translate(self) -> EmojiReaction:
        return EmojiReaction(
            chat_id=self.payload.chat_id,
            message_id=self.payload.message_id,
            counters=self.payload.reaction_info.counters,
            total_count=self.payload.reaction_info.total_count,
            your_reaction=self.payload.reaction_info.your_reaction,
        )



# TRANSLATE_MODELS = [
#     PushTranslateModel,
# ]
#
# TRANSLATE_MODELS = {
#     model.opcode.value: model
#     for model in TRANSLATE_MODELS
# }

TRANSLATE_MODELS = {
    Opcode.PUSH_NOTIFICATION: PushTranslateModel,
    Opcode.MESSAGE_REACTION_UPDATE: EmojiReactionModel,
}


def translate(update: Envelope) -> BaseMaxObject | Envelope:
    translate_model = TRANSLATE_MODELS.get(update.opcode, None)
    if not translate_model:
        return update

    print(f'PAYLOAD: {update.model_dump()}')
    translate_model = translate_model(**update.model_dump())

    return translate_model.translate()


FILE_TYPES = {
    VideoAttachment: Video,
    PhotoAttachment: Photo,
    FileAttachment: File,
    'fallback': File,
}


async def upload_file(data: bytes, typeof: type[BaseFile]):
    translate_model = TRANSLATE_MODELS.get(typeof, None)

    if not translate_model:
        translate_model = FILE_TYPES['fallback']


    loaded_attachment = translate_model.upload()