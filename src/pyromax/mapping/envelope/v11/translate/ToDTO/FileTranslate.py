from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic, cast, Optional

from typing_extensions import Self, TYPE_CHECKING

import aiohttp
from pydantic import BaseModel, Field, PrivateAttr

from ...payloads.requests import FileToPayloadRequest, PhotoToPayloadRequest, VideoToPayloadRequest

# from ...payloads.models import BaseFilePayloadMapping, VideoPayloadMapping, PhotoPayloadMapping, FilePayloadMapping
from ......models import VideoAttachment, FileAttachment, PhotoAttachment, BaseFileAttachment
from ...constants import Opcode
from ...payloads.models import PhotoMappingModel, VideoMappingModel, FileMappingModel, BaseFileMappingModel
from .....bases import BaseMapper
from ...methods import GetFileLinkMethod
from ......exceptions import DownloadFileError

if TYPE_CHECKING:
    from ......protocol import BaseMaxProtocol

BodyType = TypeVar('BodyType')
DumpReturn = TypeVar('DumpReturn', bound=BaseFileMappingModel, covariant=True)

class BaseFileMapping(BaseFileAttachment, BaseModel, Generic[BodyType, DumpReturn], ABC):
    data: bytes | None = Field(repr=False)
    url: str | None = None
    uploaded: bool = False
    file_size: int
    file_name: str | None = None


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


    @abstractmethod
    def dump_it(self) -> list[DumpReturn]:
        pass


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


    @staticmethod
    @abstractmethod
    async def get_url_to_download(mapper: BaseMapper[BaseMaxProtocol[Any, Any]], file: Any, **kwargs: Any) -> str | None: pass


class PhotoMapping(BaseFileMapping[Optional[dict[str, bytes]], PhotoMappingModel], PhotoAttachment):
    photo_ids: list[str] = []
    photo_tokens: list[str] = []


    def dump_it(self) -> list[PhotoMappingModel]:
        dumped = []
        for i, photo in enumerate(self.to_payload):
            dumped.append(
                PhotoMappingModel(
                    type='PHOTO',
                    photo_id=self.photo_ids[i],
                    **photo
                )
            )
        return dumped


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


    @staticmethod
    async def get_url_to_download(
            mapper: BaseMapper[BaseMaxProtocol[Any, Any]],
            file: PhotoMappingModel,
            **kwargs: Any
    ) -> str | None:
        return file.base_url


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


class VideoMapping(BaseFileMapping[Optional[bytes], VideoMappingModel], VideoAttachment):
    token: str
    video_id: int


    @staticmethod
    async def get_url_to_download(
            mapper: BaseMapper[BaseMaxProtocol[Any, Any]],
            file: VideoMappingModel,
            **kwargs: Any
    ) -> str | None:
        quality = kwargs.get('quality', 'MP4_720')
        response_future = await mapper.protocol.send(
            method=GetFileLinkMethod(
                opcode=Opcode.GET_VIDEO,
                file=file
            )
        )
        response_envelope = await response_future
        response = response_envelope.payload
        url = response.get(quality)
        if url is None:
            for value in response.values():
                if isinstance(value, str) and value.startswith('https://maxvd'):
                    return value
        return cast(str, url)


    @property
    def to_payload(self) -> list[dict[str, Any]]:
        return [
            VideoToPayloadRequest(
                type='VIDEO',
                video_id=self.video_id,
                token=self.token
            ).model_dump(by_alias=True),
        ]


    def dump_it(self) -> list[VideoMappingModel]:
        return [
            VideoMappingModel(
                type='VIDEO',
                video_id=self.video_id,
                token=self.token
            )
        ]


class FileMapping(BaseFileMapping[Optional[bytes], FileMappingModel], FileAttachment):
    token: str
    file_id: int


    @staticmethod
    async def get_url_to_download(
            mapper: BaseMapper[BaseMaxProtocol[Any, Any]],
            file: VideoMappingModel,
            **kwargs: Any
    ) -> str | None:
        response_future = await mapper.protocol.send(
            method=GetFileLinkMethod(
                opcode=Opcode.GET_FILE,
                file=file
            )
        )

        response_envelope = await response_future
        response = response_envelope.payload
        url = response.get('url')

        return cast(str, url)

    @property
    def to_payload(self) -> list[dict[str, Any]]:
        return [
            FileToPayloadRequest(
                type='FILE',
                file_id=self.file_id,
            ).model_dump(by_alias=True),
        ]


    def dump_it(self) -> list[FileMappingModel]:
        return [
            FileMappingModel(
                type='FILE',
                token=self.token,
                **self.to_payload[0],
            )
        ]


FILE_TYPES: dict[type[BaseFileAttachment], type[BaseFileMapping[Any, BaseFileMappingModel]]] = {
    VideoAttachment: VideoMapping,
    PhotoAttachment: PhotoMapping,
    FileAttachment: FileMapping,
}


FALLBACK_MODEL: type[BaseFileMapping[Any, BaseFileMappingModel]] = FileMapping


FILE_OPCODES: dict[type[BaseFileAttachment], int] = {
    VideoAttachment: Opcode.CREATE_VIDEO,
    PhotoAttachment: Opcode.CREATE_PHOTO,
    FileAttachment: Opcode.CREATE_FILE,
}


FALLBACK_FILE_OPCODE = Opcode.CREATE_FILE


async def upload_file(data: bytes | None, typeof: type[BaseFileAttachment], upload_url: str | None = None, uploaded: bool = False, **kwargs: Any) -> list[BaseFileMappingModel]:
    translate_model = FILE_TYPES.get(typeof, FALLBACK_MODEL)
    loaded_attachment = await translate_model.create_file_obj(
        data=data,
        upload_url=cast(str, upload_url),
        uploaded=uploaded,
        **kwargs
    )

    return loaded_attachment.dump_it()


MAPPING_MODEL_TO_FILE_MAPPING: dict[type[BaseFileMappingModel], type[BaseFileMapping[Any, BaseFileMappingModel]]] = {
    PhotoMappingModel: PhotoMapping,
    VideoMappingModel: VideoMapping,
    FileMappingModel: FileMapping
}


async def get_file_url(mapper: BaseMapper[BaseMaxProtocol[Any, Any]], file: BaseFileMappingModel, **kwargs: Any) -> str | None:
    if not file.uploaded:
        raise DownloadFileError('File has not been uploaded to chat, cannot download it')

    translate_model = MAPPING_MODEL_TO_FILE_MAPPING[type(file)]

    return await translate_model.get_url_to_download(file=file, mapper=mapper, **kwargs)