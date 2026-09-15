from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic, cast, Optional

from typing_extensions import Self, TYPE_CHECKING

import aiohttp
from pydantic import BaseModel, Field

from ...payloads.requests import (
    FileToPayloadRequest,
    PhotoToPayloadRequest,
    VideoToPayloadRequest,
)

# from ...payloads.models import BaseFilePayloadMapping, VideoPayloadMapping, PhotoPayloadMapping, FilePayloadMapping
from ......models.Attachments import (
    VideoAttachment,
    VoiceAttachment,
    VideoNoteAttachment,
    FileAttachment,
    PhotoAttachment,
    BaseFileAttachment,
)
from ...constants import Opcode
from ...payloads.models import (
    PhotoMappingModel,
    VideoMappingModel,
    VoiceMappingModel,
    VideoNoteMappingModel,
    FileMappingModel,
    BaseFileMappingModel,
)
from .....bases import BaseMapper
from ...methods.immutable import GetFileLinkMethod
from ......exceptions import DownloadFileError

if TYPE_CHECKING:
    from ......protocol import BaseMaxProtocol

BodyType = TypeVar("BodyType")
DumpReturn = TypeVar("DumpReturn", bound=BaseFileMappingModel, covariant=True)


class BaseFileMapping(
    BaseFileAttachment,
    BaseModel,
    Generic[BodyType, DumpReturn],
    ABC,
):
    data: bytes | None = Field(repr=False)
    url: str | None = None
    uploaded: bool = False
    file_size: int
    file_name: str | None = None

    @classmethod
    async def create_file_obj(
        cls,
        data: bytes | None,
        upload_url: str,
        uploaded: bool = False,
        file_size: int | None = None,
        **kwargs: Any,
    ) -> Self:
        """Create file obj.

        :param data: Contextual data passed through the processing pipeline.
        :type data: bytes | None
        :param upload_url: The upload url value.
        :type upload_url: str
        :param uploaded: The uploaded value.
        :type uploaded: bool
        :param file_size: The file size value.
        :type file_size: int | None
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The current instance.
        :rtype: Self
        :raises RuntimeError: If need upload_url or uploaded.
        :raises RuntimeError: If need data or uploaded.
        """
        if not upload_url and not uploaded:
            raise RuntimeError("need upload_url or uploaded")
        if not data and not uploaded:
            raise RuntimeError("need data or uploaded")
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
        """Dump it.

        :returns: The resulting collection.
        :rtype: list[DumpReturn]
        """
        pass

    async def _upload_data_to_url(self, upload_url: str) -> None:
        """Upload data to url.

        :param upload_url: The upload url value.
        :type upload_url: str
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=upload_url,
                data=self.body,
                headers=self.headers,
            ) as response:
                await self._parse_response(response=response)

    @property
    def headers(self) -> dict[str, str] | None:
        """Just base headers for Video/File and etc.
        In Photo class this getter need to overwrite

        :returns: The resulting dict[str, str] | None value.
        :rtype: dict[str, str] | None
        """
        return {
            "Content-Disposition": f"attachment; filename={self.file_name}",
            "Content-Range": f"0-{self.file_size - 1}/{self.file_size}",
            "Content-Length": str(self.file_size),
            "Connection": "keep-alive",
        }

    @property
    def body(self) -> BodyType:
        """Body.

        :returns: The resulting BodyType value.
        :rtype: BodyType
        """
        return cast(BodyType, self.data)

    @property
    @abstractmethod
    def to_payload(self) -> list[dict[str, Any]]:
        """To payload.

        :returns: The resulting collection.
        :rtype: list[dict[str, Any]]
        """
        pass

    async def _parse_response(self, response: aiohttp.ClientResponse) -> None:
        """Parse response.

        :param response: Protocol response to process.
        :type response: aiohttp.ClientResponse
        """
        self.uploaded = True

    @staticmethod
    @abstractmethod
    async def get_url_to_download(
        mapper: BaseMapper[BaseMaxProtocol[Any, Any], BaseFileMappingModel],
        file: Any,
        **kwargs: Any,
    ) -> str | None:
        """Retrieve url to download.

        :param mapper: Mapper backend or mapper instance.
        :type mapper: BaseMapper[BaseMaxProtocol[Any, Any], BaseFileMappingModel]
        :param file: File attachment to process.
        :type file: Any
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting str | None value.
        :rtype: str | None
        """
        pass


class PhotoMapping(
    BaseFileMapping[Optional[dict[str, bytes]], PhotoMappingModel],
    PhotoAttachment,
):
    photo_ids: list[str] = []
    photo_tokens: list[str] = []

    def dump_it(self) -> list[PhotoMappingModel]:
        """Dump it.

        :returns: The resulting collection.
        :rtype: list[PhotoMappingModel]
        """
        dumped = []
        for i, photo in enumerate(self.to_payload):
            dumped.append(
                PhotoMappingModel(
                    type="PHOTO",
                    uploaded=self.uploaded,
                    photo_id=(
                        self.photo_ids[i]
                        if photo["photoToken"] in self.photo_tokens
                        else None
                    ),
                    **photo,
                )
            )
        return dumped

    @property
    def headers(self) -> None:
        """Photo not need headers"""
        return None

    @property
    def body(self) -> dict[str, bytes]:
        """Body.

        :returns: The resulting dict[str, bytes] value.
        :rtype: dict[str, bytes]
        :raises RuntimeError: If try a upload photo with None data attr.
        """
        if self.data is None:
            raise RuntimeError("try a upload photo with None data attr")
        return {"file": self.data}

    @staticmethod
    async def get_url_to_download(
        mapper: BaseMapper[BaseMaxProtocol[Any, Any], BaseFileMappingModel],
        file: PhotoMappingModel,
        **kwargs: Any,
    ) -> str | None:
        """Retrieve url to download.

        :param mapper: Mapper backend or mapper instance.
        :type mapper: BaseMapper[BaseMaxProtocol[Any, Any], BaseFileMappingModel]
        :param file: File attachment to process.
        :type file: PhotoMappingModel
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting str | None value.
        :rtype: str | None
        """
        return file.base_url

    async def _parse_response(self, response: aiohttp.ClientResponse) -> None:
        """Parse response.

        :param response: Protocol response to process.
        :type response: aiohttp.ClientResponse
        """
        json: dict[str, Any] = await response.json()
        photos: dict[str, Any] = json["photos"]
        for photo_id, photo_token in photos.items():
            self.photo_ids.append(photo_id)
            self.photo_tokens.append(photo_token["token"])

    @property
    def to_payload(self) -> list[dict[str, Any]]:
        """To payload.

        :returns: The resulting collection.
        :rtype: list[dict[str, Any]]
        """
        photos = []
        for token in self.photo_tokens:
            photos.append(
                PhotoToPayloadRequest(type="PHOTO", photo_token=token).model_dump(
                    by_alias=True
                )
            )
        return photos


class VideoMapping(
    BaseFileMapping[Optional[bytes], VideoMappingModel],
    VideoAttachment,
):
    token: str
    video_id: int

    @staticmethod
    async def get_url_to_download(
        mapper: BaseMapper[BaseMaxProtocol[Any, Any], BaseFileMappingModel],
        file: VideoMappingModel,
        **kwargs: Any,
    ) -> str | None:
        """Retrieve url to download.

        :param mapper: Mapper backend or mapper instance.
        :type mapper: BaseMapper[BaseMaxProtocol[Any, Any], BaseFileMappingModel]
        :param file: File attachment to process.
        :type file: VideoMappingModel
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting str | None value.
        :rtype: str | None
        """
        quality = kwargs.get("quality", "MP4_720")
        response_future = await mapper.protocol.send(
            method=GetFileLinkMethod(opcode=Opcode.GET_VIDEO, file=file)
        )
        response_envelope = await response_future
        response = response_envelope.payload
        url = response.get(quality)
        if url is None:
            for value in response.values():
                if isinstance(value, str) and value.startswith("https://maxvd"):
                    return value
        return cast(str, url)

    @property
    def to_payload(self) -> list[dict[str, Any]]:
        """To payload.

        :returns: The resulting collection.
        :rtype: list[dict[str, Any]]
        """
        return [
            VideoToPayloadRequest(
                type="VIDEO",
                video_id=self.video_id,
                token=self.token,
            ).model_dump(by_alias=True),
        ]

    def dump_it(self) -> list[VideoMappingModel]:
        """Dump it.

        :returns: The resulting collection.
        :rtype: list[VideoMappingModel]
        """
        return [
            VideoMappingModel(
                type="VIDEO",
                video_id=self.video_id,
                token=self.token,
                uploaded=self.uploaded,
            )
        ]


class VideoNoteMapping(
    VideoMapping,
    BaseFileMapping[Optional[bytes], VideoNoteMappingModel],
    VideoNoteAttachment,
):
    def dump_it(self) -> list[VideoNoteMappingModel]:  # type: ignore[override]
        """Dump it.

        :returns: The resulting collection.
        :rtype: list[VideoNoteMappingModel]
        """
        return [
            VideoNoteMappingModel(
                type="VIDEO",
                video_id=self.video_id,
                token=self.token,
                uploaded=self.uploaded,
                video_type=1,
            )
        ]


class VoiceMapping(
    VideoMapping,
    BaseFileMapping[Optional[bytes], VideoMappingModel],
    VoiceAttachment,
):

    @property
    def headers(self) -> dict[str, str] | None:
        """Headers.

        :returns: The resulting dict[str, str] | None value.
        :rtype: dict[str, str] | None
        """
        return {
            "Content-Disposition": f"attachment; filename={self.file_name}",
            "Content-Range": f"0-{self.file_size - 1}/{self.file_size}",
            "Content-Length": str(self.file_size),
            "Connection": "keep-alive",
            # "Content-Type": "application/octet-stream",
        }

    def dump_it(self) -> list[VoiceMappingModel]:  # type: ignore[override]
        """Dump it.

        :returns: The resulting collection.
        :rtype: list[VoiceMappingModel]
        """
        return [
            VoiceMappingModel(
                type="AUDIO",
                audio_id=self.video_id,
                token=self.token,
                uploaded=self.uploaded,
            )
        ]


class FileMapping(
    BaseFileMapping[Optional[bytes], FileMappingModel],
    FileAttachment,
):
    token: str
    file_id: int

    @staticmethod
    async def get_url_to_download(
        mapper: BaseMapper[BaseMaxProtocol[Any, Any], BaseFileMappingModel],
        file: VideoMappingModel,
        **kwargs: Any,
    ) -> str | None:
        """Retrieve url to download.

        :param mapper: Mapper backend or mapper instance.
        :type mapper: BaseMapper[BaseMaxProtocol[Any, Any], BaseFileMappingModel]
        :param file: File attachment to process.
        :type file: VideoMappingModel
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting str | None value.
        :rtype: str | None
        """
        response_future = await mapper.protocol.send(
            method=GetFileLinkMethod(opcode=Opcode.GET_FILE, file=file)
        )

        response_envelope = await response_future
        response = response_envelope.payload
        url = response.get("url")

        return cast(str, url)

    @property
    def to_payload(self) -> list[dict[str, Any]]:
        """To payload.

        :returns: The resulting collection.
        :rtype: list[dict[str, Any]]
        """
        return [
            FileToPayloadRequest(
                type="FILE",
                file_id=self.file_id,
            ).model_dump(by_alias=True),
        ]

    def dump_it(self) -> list[FileMappingModel]:
        """Dump it.

        :returns: The resulting collection.
        :rtype: list[FileMappingModel]
        """
        return [
            FileMappingModel(
                type="FILE",
                token=self.token,
                uploaded=self.uploaded,
                **self.to_payload[0],
            )
        ]


FILE_TYPES: dict[
    type[BaseFileAttachment], type[BaseFileMapping[Any, BaseFileMappingModel]]
] = {
    VideoAttachment: VideoMapping,
    VoiceAttachment: VoiceMapping,
    VideoNoteAttachment: VideoNoteMapping,
    PhotoAttachment: PhotoMapping,
    FileAttachment: FileMapping,
}


FALLBACK_MODEL: type[BaseFileMapping[Any, BaseFileMappingModel]] = FileMapping


FILE_OPCODES: dict[type[BaseFileAttachment], int] = {
    VideoAttachment: Opcode.CREATE_VIDEO,
    VideoNoteAttachment: Opcode.CREATE_VIDEO,
    VoiceAttachment: Opcode.CREATE_VIDEO,
    PhotoAttachment: Opcode.CREATE_PHOTO,
    FileAttachment: Opcode.CREATE_FILE,
}

UPLOAD_TYPES: dict[type[BaseFileAttachment], int] = {
    VideoNoteAttachment: 1,
    VoiceAttachment: 2,
}
UPLOADER_TYPES: dict[type[BaseFileAttachment], int] = {
    VideoNoteAttachment: 1,
    VoiceAttachment: 1,
}

FALLBACK_FILE_OPCODE = Opcode.CREATE_FILE


async def upload_file(
    data: bytes | None,
    typeof: type[BaseFileAttachment],
    upload_url: str | None = None,
    uploaded: bool = False,
    **kwargs: Any,
) -> list[BaseFileMappingModel]:
    """Upload file.

    :param data: Contextual data passed through the processing pipeline.
    :type data: bytes | None
    :param typeof: Attachment class that determines the upload type.
    :type typeof: type[BaseFileAttachment]
    :param upload_url: The upload url value.
    :type upload_url: str | None
    :param uploaded: The uploaded value.
    :type uploaded: bool
    :param kwargs: Keyword arguments forwarded to the wrapped callable.
    :type kwargs: Any
    :returns: The resulting collection.
    :rtype: list[BaseFileMappingModel]
    """
    translate_model = FILE_TYPES.get(typeof, FALLBACK_MODEL)
    loaded_attachment = await translate_model.create_file_obj(
        data=data, upload_url=cast(str, upload_url), uploaded=uploaded, **kwargs
    )

    return loaded_attachment.dump_it()


MAPPING_MODEL_TO_FILE_MAPPING: dict[
    type[BaseFileMappingModel], type[BaseFileMapping[Any, BaseFileMappingModel]]
] = {
    PhotoMappingModel: PhotoMapping,
    VideoMappingModel: VideoMapping,
    FileMappingModel: FileMapping,
    # VoiceAttachment: VoiceMapping,
    # VideoNoteAttachment: VideoMapping,
}


async def get_file_url(
    mapper: BaseMapper[BaseMaxProtocol[Any, Any], BaseFileMappingModel],
    file: BaseFileMappingModel,
    **kwargs: Any,
) -> str | None:
    """Retrieve file url.

    :param mapper: Mapper backend or mapper instance.
    :type mapper: BaseMapper[BaseMaxProtocol[Any, Any], BaseFileMappingModel]
    :param file: File attachment to process.
    :type file: BaseFileMappingModel
    :param kwargs: Keyword arguments forwarded to the wrapped callable.
    :type kwargs: Any
    :returns: The resulting str | None value.
    :rtype: str | None
    :raises DownloadFileError: If file has not been uploaded to chat, cannot download it(Most likely, you uploaded the attachment but did not send a message with it.).
    """

    if not file.uploaded:
        raise DownloadFileError(
            "File has not been uploaded to chat, cannot download it(Most likely, you uploaded the attachment but did not send a message with it.)"
        )

    translate_model = MAPPING_MODEL_TO_FILE_MAPPING[type(file)]

    return await translate_model.get_url_to_download(file=file, mapper=mapper, **kwargs)
