import abc
from typing import Any, ClassVar
import aiohttp
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from .OpcodeEnum import Opcode
from pyromax.mixins import DataBodyMixin, FormDataBodyMixin


class BaseFile(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    max_client: Any | None = Field(default=None, exclude=True)
    url: str | None = None
    uploaded: bool = Field(default=False)

    _data_to_upload: Any = PrivateAttr(default=None)
    _filename: str | None = PrivateAttr(default=None)
    headers: dict | None = Field(default=None, exclude=True)

    async def send_create_request(self):
        return await self.max_client.send_and_receive(opcode=self._opcode, payload={"count": 1})

    @classmethod
    async def upload_new(cls, max_client, data, filename=None) -> 'BaseFile':
        """
        Create object, get URL from server and load bytes
        """

        instance = cls(max_client=max_client, uploaded=False)
        instance._data_to_upload = data
        instance._filename = filename

        await instance.create_cell_for_file()

        await instance.upload_data_to_url()

        return instance

    async def upload_data_to_url(self):
        if not self.url or self._data_to_upload is None:
            return

        try:
            headers = None
            if self.headers:
                headers = self.headers
            elif hasattr(self, '_set_headers') and self._filename:
                self.file_size = len(self._data_to_upload)
                self._set_headers(self.file_size, self._filename)
                headers = self.headers

            async with aiohttp.ClientSession() as session:
                if hasattr(self, 'get_body'):
                    data = self.get_body(self._data_to_upload)
                else:
                    data = self._data_to_upload

                async with session.post(url=self.url, data=data, headers=headers) as response:
                    await self._parse_response(response)

        finally:
            self._data_to_upload = None

    @abc.abstractmethod
    async def create_cell_for_file(self):
        pass

    @abc.abstractmethod
    async def _parse_response(self, response):
        pass


class Photo(FormDataBodyMixin, BaseFile):
    photo_token: str = Field(default='', validation_alias='photoToken')
    base_url: str | None = Field(default=None, validation_alias='baseUrl')
    photo_id: int | None = Field(default=None, validation_alias='photoId')

    _opcode: ClassVar[int] = Opcode.CREATE_PHOTO.value

    async def create_cell_for_file(self):
        response = await self.send_create_request()
        self.url = response.get('payload', {}).get('url')

    async def _parse_response(self, response):
        photos = (await response.json())['photos']
        photo_id = list(photos.keys())[0]
        self.photo_token = photos[photo_id]['token']
        self.uploaded = True


class Video(DataBodyMixin, BaseFile):
    token: str = Field(default='', validation_alias='token')
    video_id: int = Field(default='', validation_alias='videoId')
    video_type: int | None = Field(default=None, validation_alias='videoType')

    _opcode: ClassVar[int] = Opcode.CREATE_VIDEO.value

    file_size: int | None = Field(default=None, exclude=True)

    async def create_cell_for_file(self):
        if hasattr(self, '_get_payload_info'):
            root = await self._get_payload_info()
        else:
            raise NotImplementedError("Implement _get_payload_info or logic here")
        self.url = root['url']
        self.video_id = root['videoId']
        self.token = root['token']


    async def _parse_response(self, response):
        self.uploaded = True


class File(DataBodyMixin, BaseFile):
    file_id: int = Field(default='', validation_alias='fileId')
    file_size: int | None = Field(default=None, validation_alias='size')
    file_token: str = Field(default='', validation_alias='token')

    _opcode: ClassVar[int] = Opcode.CREATE_FILE.value


    async def create_cell_for_file(self):
        if hasattr(self, '_get_payload_info'):
            root = await self._get_payload_info()
        else:
            raise NotImplementedError("Implement _get_payload_info")
        self.url = root.get('url')
        self.file_id = root.get('fileId')
        self.file_token = root.get('token')


    async def _parse_response(self, response):
        self.uploaded = True
