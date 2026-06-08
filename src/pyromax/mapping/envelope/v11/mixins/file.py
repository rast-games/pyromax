from __future__ import annotations
import logging

import aiohttp

from collections.abc import Callable, Coroutine
from typing import Any, cast, TYPE_CHECKING

from ..methods.immutable import GetUrlToUploadFileMethod
from ..payloads.responses import ResponseWithUrl
from ..payloads.models import BaseFileMappingModel
from .....models import BaseFileAttachment
from ..translate.ToDTO import FILE_OPCODES, FALLBACK_FILE_OPCODE, get_file_url, upload_file
from ....bases import BaseMapper
from .....protocol import BaseMaxProtocol, Envelope
from .....exceptions import DownloadFileError

from .MixinProtocol import MixinProtocol

class FileMixin(MixinProtocol):
    async def _create_cell_for_file(
            self,
            opcode: int,
            count: int = 1,
    ) -> dict[str, Any]:
        response = await self.send(
            method=GetUrlToUploadFileMethod(type_of_file_opcode=opcode, count=count)
        )

        payload = ResponseWithUrl(
            **response.payload
        ).model_dump(exclude_none=True)

        return payload

    async def upload_file(
            self,
            data: bytes | None,
            typeof: type[BaseFileAttachment],
            count: int = 1,
            file_name: str | None = None,
            uploaded: bool = False,
            **kwargs: Any
    ) -> list[BaseFileMappingModel]:
        payload = {}
        if not uploaded:
            payload = await self._create_cell_for_file(
                opcode=FILE_OPCODES.get(typeof, FALLBACK_FILE_OPCODE),
                count=count,
            )

        uploaded_file = await upload_file(
            data=data,
            typeof=typeof,
            file_name=file_name,
            uploaded=uploaded,
            **payload,
            **kwargs
        )

        return uploaded_file

    async def download_file(
            self,
            file: BaseFileMappingModel,
            cookies_to_download: dict[str, str] | None = None,
            headers_to_download: dict[str, str] | None = None,
            **kwargs: Any
    ) -> tuple[bytes, dict[str, str]] | tuple[None, None]:
        url = await get_file_url(file=file, mapper=cast(BaseMapper[BaseMaxProtocol[Any, Any], Any], self), **kwargs)
        if url is None:
            self._logger.warning('cannot get a download url for file')
            return None, None
        api = self.max_api
        if api is None:
            raise RuntimeError('max_api must be set')
        opts = api.transport_options or {}
        user_agent_header = opts.get(
            'user_agent_header') or 'Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0'

        headers: dict[str, str]
        if headers_to_download is None:
            headers = {
                "User-Agent": user_agent_header,
                "Accept": "*/*",
                "Referer": "https://ok.ru/"
            }
        else:
            headers = headers_to_download

        cookies: dict[str, str]
        if cookies_to_download is None:
            cookies = {
                "tstc": "p"
            }
        else:
            cookies = cookies_to_download
        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
            async with session.get(url=url) as response:
                if response.status > 299:
                    self._logger.warning('Download failed for file')
                    raise DownloadFileError('Download failed for file')
                chunks = []
                async for chunk in response.content.iter_chunked(8192):
                    chunks.append(chunk)
                return b''.join(chunks), dict(response.headers)
        return None, None