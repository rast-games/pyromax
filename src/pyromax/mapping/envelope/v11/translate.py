from abc import ABC, abstractmethod
from typing import cast, Any
from typing_extensions import Self

from src.pyromax.models import BaseMaxObject, Message, EmojiReaction, VideoAttachment, FileAttachment, PhotoAttachment, \
    BaseFileAttachment, MessageLink
from src.pyromax.protocol.envelope import Envelope
from .constants import Opcode
from .payloads import PushPayloadModel, EmojiReactionUpdateModel, FileToPayloadModel, PhotoToPayloadModel, \
    VideoToPayloadModel, MessageModel

from pydantic import BaseModel, Field
import aiohttp


class TranslateModel(BaseModel, ABC):
    payload: dict


    @abstractmethod
    def translate(self, context) -> BaseMaxObject: pass


class PushTranslateModel(TranslateModel):
    payload: PushPayloadModel


    def translate(self, context: Any) -> Message:
        self.payload.message.chat_id = self.payload.chat_id


        def translate_message(message: MessageModel, chat_id: int = None) -> Message:
            message_link = message.link
            message.chat_id = chat_id
            data = {
                'chat_id': chat_id,
                'text': message.text,
                'message_id': int(message.id),
                'status': message.status,
                'time': message.time,
                'cid': message.cid,
                'type': message.type,
                'attaches': message.attaches,
                'elements': message.elements,
                'sender_id': message.sender,
            }
            if not message_link:
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


        return translate_message(self.payload.message, self.payload.chat_id)


class EmojiReactionModel(TranslateModel):
    payload: EmojiReactionUpdateModel


    def translate(self, context: Any) -> EmojiReaction:

        data = {
            'chat_id': self.payload.chat_id,
            'message_id': self.payload.message_id,
            'counters': self.payload.reaction_info.counters,
            'total_count': self.payload.reaction_info.total_count,
            'your_reaction': self.payload.reaction_info.your_reaction,
        }

        return EmojiReaction.model_validate(
            obj=data,
            context=context,
        )


TRANSLATE_MODELS = {
    Opcode.PUSH_NOTIFICATION: PushTranslateModel,
    Opcode.MESSAGE_REACTION_UPDATE: EmojiReactionModel,
}


def translate(update: Envelope, context: Any) -> BaseMaxObject | Envelope:
    translate_model = TRANSLATE_MODELS.get(update.opcode, None)
    if not translate_model:
        return update
    translate_model = translate_model(**update.model_dump())
    return translate_model.translate(context=context)


class BaseFile(BaseModel, ABC):
    data: bytes | None = Field(repr=False)
    url: str | None = None
    uploaded: bool = False
    file_size: int
    file_name: str | None = None


    @classmethod
    async def create_file_obj(cls, data: bytes | None, upload_url: str, uploaded: bool = False, file_size: int | None = None, **kwargs) -> Self:
        if not upload_url and not uploaded:
            raise RuntimeError('need upload_url or uploaded')
        if not data and not uploaded:
            raise RuntimeError('need data or uploaded')
        if not file_size:
            if data:
                file_size = len(data)
            else:
                file_size = 0
        self = cls(data=data, uploaded=uploaded, file_size=file_size, **kwargs)
        if uploaded:
            return self
        await self._upload_data_to_url(upload_url=upload_url)
        return self


    async def _upload_data_to_url(
            self,
            upload_url: str
    ):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    url=upload_url,
                    data=self.body,
                    headers=self.headers,
            ) as response:
                await self._parse_response(response=response)


    @property
    def headers(self) -> dict[str, str] | None:
        """
        Just base headers for Video/File and etc.
        In Photo class this getter need to overwrite
        """
        return {
            "Content-Disposition": f"attachment; filename={self.file_name}",
            "Content-Range": f"0-{self.file_size - 1}/{self.file_size}",
            "Content-Length": str(self.file_size),
            "Connection": "keep-alive",
        }


    @property
    def body(self) -> bytes | dict[str, bytes]:
        return self.data


    @property
    @abstractmethod
    def to_payload(self) -> list[dict]: pass


    async def _parse_response(self, response: aiohttp.ClientResponse) -> None:
        self.uploaded = True


class Photo(BaseFile, PhotoAttachment):
    photo_ids: list[str] = []
    photo_tokens: list[str] = []


    @property
    def headers(
            self
    ) -> None:
        """Photo not need headers"""
        return None


    @property
    def body(
            self
    ) -> dict[str, bytes]:
        return {
            'file': self.data
        }


    async def _parse_response(self, response: aiohttp.ClientResponse) -> None:
        json: dict = await response.json()
        photos: dict = json['photos']
        for photo_id, photo_token in photos.items():
            self.photo_ids.append(photo_id)
            self.photo_tokens.append(photo_token['token'])


    @property
    def to_payload(self) -> list[dict]:
        photos = []
        for token in self.photo_tokens:
            photos.append(
                PhotoToPayloadModel(
                    type='PHOTO',
                    photo_token=token
                ).model_dump(by_alias=True)
            )
        return photos


class Video(BaseFile, VideoAttachment):
    token: str
    video_id: int


    @property
    def to_payload(self) -> list[dict]:
        return [
            VideoToPayloadModel(
                type='VIDEO',
                video_id=self.video_id,
                token=self.token
            ).model_dump(by_alias=True),
        ]


class File(BaseFile, FileAttachment):
    token: str
    file_id: int


    @property
    def to_payload(self) -> list[dict]:
        return [
            FileToPayloadModel(
                type='FILE',
                file_id=self.file_id,
            ).model_dump(by_alias=True),
        ]


FILE_TYPES: dict[type[BaseFileAttachment], type[BaseFile]] = {
    VideoAttachment: Video,
    PhotoAttachment: Photo,
    FileAttachment: File,
}


FALLBACK_MODEL: type[BaseFile] = File


FILE_OPCODES: dict[type[BaseFileAttachment], int] = {
    VideoAttachment: Opcode.CREATE_VIDEO,
    PhotoAttachment: Opcode.CREATE_PHOTO,
    FileAttachment: Opcode.CREATE_FILE,
}


FALLBACK_FILE_OPCODE = Opcode.CREATE_FILE


async def upload_file(data: bytes | None, typeof: type[BaseFileAttachment], upload_url: str = None, uploaded: bool = False, **kwargs) -> BaseFileAttachment:
    translate_model = FILE_TYPES.get(typeof, FALLBACK_MODEL)
    loaded_attachment = await translate_model.create_file_obj(
        data=data,
        upload_url=upload_url,
        uploaded=uploaded,
        **kwargs
    )
    return cast(BaseFileAttachment, loaded_attachment)