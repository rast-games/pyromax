from __future__ import annotations
import logging
from http import HTTPStatus

import aiohttp

from collections.abc import Callable, Coroutine
from typing import Any, cast, TYPE_CHECKING

from ..methods.immutable import GetUrlToUploadFileMethod
from ..payloads.responses import ResponseWithUrl
from ..payloads.models import BaseFileMappingModel
from .....models import BaseFileAttachment
from ..translate.ToDTO import (
    FILE_OPCODES,
    FALLBACK_FILE_OPCODE,
    UPLOADER_TYPES,
    UPLOAD_TYPES,
    get_file_url,
    upload_file,
)
from ....bases import BaseMapper
from .....protocol import BaseMaxProtocol, Envelope
from .....exceptions import DownloadFileError

from .MixinProtocol import MixinProtocol


class FileMixin(MixinProtocol):
    async def _create_cell_for_file(
        self,
        opcode: int,
        upload_type: int = 0,
        uploader_type: int = 0,
        count: int = 1,
    ) -> dict[str, Any]:
        """Create cell for file.

        :param opcode: The opcode value.
        :type opcode: int
        :param upload_type: The upload type value.
        :type upload_type: int
        :param uploader_type: The uploader type value.
        :type uploader_type: int
        :param count: Maximum number of items to retrieve.
        :type count: int
        :returns: The resulting dict[str, Any] value.
        :rtype: dict[str, Any]
        """
        response = await self.send(
            method=GetUrlToUploadFileMethod(
                type_of_file_opcode=opcode,
                count=count,
                uploader_type=uploader_type,
                upload_type=upload_type,
            )
        )

        payload = ResponseWithUrl(**response.payload).model_dump(exclude_none=True)

        return payload

    async def upload_file(
        self,
        data: bytes | None,
        typeof: type[BaseFileAttachment],
        count: int = 1,
        file_name: str | None = None,
        uploaded: bool = False,
        **kwargs: Any,
    ) -> list[BaseFileMappingModel]:
        """Upload file.

        :param data: Contextual data passed through the processing pipeline.
        :type data: bytes | None
        :param typeof: Attachment class that determines the upload type.
        :type typeof: type[BaseFileAttachment]
        :param count: Maximum number of items to retrieve.
        :type count: int
        :param file_name: The file name value.
        :type file_name: str | None
        :param uploaded: The uploaded value.
        :type uploaded: bool
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting collection.
        :rtype: list[BaseFileMappingModel]
        """
        payload = {}
        if not uploaded:
            upload_type = UPLOAD_TYPES.get(typeof)
            uploader_type = UPLOADER_TYPES.get(typeof)

            create_cell_args = {
                "opcode": FILE_OPCODES.get(typeof, FALLBACK_FILE_OPCODE),
                "count": count,
            }
            if upload_type:
                create_cell_args["upload_type"] = upload_type
            if uploader_type:
                create_cell_args["uploader_type"] = uploader_type

            payload = await self._create_cell_for_file(
                **create_cell_args,
            )

        uploaded_file = await upload_file(
            data=data,
            typeof=typeof,
            file_name=file_name,
            uploaded=uploaded,
            **payload,
            **kwargs,
        )

        return uploaded_file

    async def download_file(
        self,
        file: BaseFileMappingModel,
        cookies_to_download: dict[str, str] | None = None,
        headers_to_download: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> tuple[bytes, dict[str, str]] | tuple[None, None]:
        """Download file.

        :param file: File attachment to process.
        :type file: BaseFileMappingModel
        :param cookies_to_download: dict[str, str] instance to process.
        :type cookies_to_download: dict[str, str] | None
        :param headers_to_download: dict[str, str] instance to process.
        :type headers_to_download: dict[str, str] | None
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting tuple[bytes, dict[str, str]] | tuple[None, None] value.
        :rtype: tuple[bytes, dict[str, str]] | tuple[None, None]
        :raises RuntimeError: If mapper not bound to max_api instance, because user_agent is None.
        :raises RuntimeError: If user_agent_header must be str.
        :raises DownloadFileError: If download failed for file.
        """
        url = await get_file_url(
            file=file,
            mapper=cast(BaseMapper[BaseMaxProtocol[Any, Any], Any], self),
            **kwargs,
        )
        if url is None:
            self._logger.warning("cannot get a download url for file")
            return None, None

        if self.user_agent is None:
            raise RuntimeError(
                "Mapper not bound to max_api instance, because user_agent is None"
            )

        user_agent_header = self.user_agent.http_user_agent

        headers: dict[str, str]
        if headers_to_download is None:
            if not isinstance(user_agent_header, str):
                raise RuntimeError("user_agent_header must be str")
            headers = {
                "User-Agent": user_agent_header,
                "Accept": "*/*",
                "Referer": "https://ok.ru/",
            }
        else:
            headers = headers_to_download

        cookies: dict[str, str]
        if cookies_to_download is None:
            cookies = {"tstc": "p"}
        else:
            cookies = cookies_to_download
        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
            async with session.get(url=url) as response:
                if response.status != HTTPStatus.OK:
                    self._logger.warning("Download failed for file")
                    raise DownloadFileError("Download failed for file")
                chunks = []
                async for chunk in response.content.iter_chunked(8192):
                    chunks.append(chunk)
                return b"".join(chunks), dict(response.headers)
        return None, None
