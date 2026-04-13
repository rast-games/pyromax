from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic, cast, Optional

from typing_extensions import Self

import aiohttp
from pydantic import BaseModel, Field, PrivateAttr

from src.pyromax.mapping.envelope.v11.payloads.requests import FileToPayloadRequest, PhotoToPayloadRequest, VideoToPayloadRequest
from src.pyromax.models import VideoAttachment, FileAttachment, PhotoAttachment, BaseFileAttachment
from src.pyromax.mapping.envelope.v11.constants import Opcode

BodyType = TypeVar('BodyType')

class BaseFileMapping(BaseFileAttachment, BaseModel, Generic[BodyType], ABC):
    data: bytes | None = Field(repr=False)
    url: str | None = None
    uploaded: bool = False
    file_size: int
    file_name: str | None = None

    # _body_type: BodyType = PrivateAttr()


    @classmethod
    async def create_file_obj(cls, data: bytes | None, upload_url: str, uploaded: bool = False, file_size: int | None = None, **kwargs: Any) -> Self:
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
    ) -> None:
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
    def body(self) -> BodyType:
        return cast(BodyType, self.data)


    @property
    @abstractmethod
    def to_payload(self) -> list[dict[str, Any]]: pass


    async def _parse_response(self, response: aiohttp.ClientResponse) -> None:
        self.uploaded = True


class PhotoMapping(BaseFileMapping[Optional[dict[str, bytes]]], PhotoAttachment):
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
        if self.data is None:
            raise RuntimeError('try a upload photo with None data attr')
        return {
            'file': self.data
        }


    async def _parse_response(self, response: aiohttp.ClientResponse) -> None:
        json: dict[str, Any] = await response.json()
        photos: dict[str, Any] = json['photos']
        for photo_id, photo_token in photos.items():
            self.photo_ids.append(photo_id)
            self.photo_tokens.append(photo_token['token'])


    @property
    def to_payload(self) -> list[dict[str, Any]]:
        photos = []
        for token in self.photo_tokens:
            photos.append(
                PhotoToPayloadRequest(
                    type='PHOTO',
                    photo_token=token
                ).model_dump(by_alias=True)
            )
        return photos


class VideoMapping(BaseFileMapping[Optional[bytes]], VideoAttachment):
    token: str
    video_id: int


    @property
    def to_payload(self) -> list[dict[str, Any]]:
        return [
            VideoToPayloadRequest(
                type='VIDEO',
                video_id=self.video_id,
                token=self.token
            ).model_dump(by_alias=True),
        ]


class FileMapping(BaseFileMapping[Optional[bytes]], FileAttachment):
    token: str
    file_id: int


    @property
    def to_payload(self) -> list[dict[str, Any]]:
        return [
            FileToPayloadRequest(
                type='FILE',
                file_id=self.file_id,
            ).model_dump(by_alias=True),
        ]


FILE_TYPES: dict[type[BaseFileAttachment], type[BaseFileMapping[Any]]] = {
    VideoAttachment: VideoMapping,
    PhotoAttachment: PhotoMapping,
    FileAttachment: FileMapping,
}


FALLBACK_MODEL: type[BaseFileMapping[Any]] = FileMapping


FILE_OPCODES: dict[type[BaseFileAttachment], int] = {
    VideoAttachment: Opcode.CREATE_VIDEO,
    PhotoAttachment: Opcode.CREATE_PHOTO,
    FileAttachment: Opcode.CREATE_FILE,
}


FALLBACK_FILE_OPCODE = Opcode.CREATE_FILE


async def upload_file(data: bytes | None, typeof: type[BaseFileAttachment], upload_url: str | None = None, uploaded: bool = False, **kwargs: Any) -> BaseFileMapping[Any]:
    translate_model = FILE_TYPES.get(typeof, FALLBACK_MODEL)
    loaded_attachment = await translate_model.create_file_obj(
        data=data,
        upload_url=cast(str, upload_url),
        uploaded=uploaded,
        **kwargs
    )
    # return cast(BaseFileAttachment, loaded_attachment)
    return loaded_attachment