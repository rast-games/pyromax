import asyncio
import abc
# import os
# import time


import aiohttp


# from maxapi.api import MaxApi
from maxapi.mixins import DataBodyMixin, FormDataBodyMixin, AsyncInitializerMixin
from maxapi.types import Opcode


class BaseFile(AsyncInitializerMixin):
    async def _init(self, max_client, data, headers = None):
        self.max_client = max_client
        self.url: str | None = None
        self.data: dict = self.get_body(data)
        await self.create_cell_for_file()
        await self.upload_data_to_url()


    @abc.abstractmethod
    async def create_cell_for_file(self):
        ...


    @abc.abstractmethod
    def get_body(self, data):
        ...


    @abc.abstractmethod
    async def _parse_response(self, response):
        ...


    async def send_create_request(self):
        return await self.max_client.send_and_receive(opcode=self.opcode, payload={
            "count": 1
        })


    async def upload_data_to_url(self):
        if not self.url:
            return
        if 'headers' in dir(self):
            headers = self.headers
        else:
            headers = None
        async with aiohttp.ClientSession() as session:
            async with session.post(url=self.url, data=self.data, headers=headers) as response:
                await self._parse_response(response)


    def __repr__(self):
        return (type(self), self.__dict__)


class Photo(FormDataBodyMixin, BaseFile):
    async def _init(self, max_client, data):
        self.photo_token: str = ''
        self.opcode: int = Opcode.CREATE_PHOTO.value
        self.uploaded: bool = False
        await super()._init(max_client, data)


    async def create_cell_for_file(self):
        response = await self.send_create_request()
        self.url = response.get('payload', {}).get('url')


    async def _parse_response(self, response):
        photos = (await response.json())['photos']
        photo_id = list(photos.keys())[0]
        self.photo_token = photos[photo_id]['token']
        self.uploaded = True


class Video(DataBodyMixin, BaseFile):
    async def _init(self, max_client, data, filename='None.mp4'):
        self.token: str = ''
        self.video_id: str = ''
        self.opcode: int = Opcode.CREATE_VIDEO.value
        self.file_size: int = len(data)
        self.uploaded: bool = False
        self._set_headers(self.file_size, filename)
        await super()._init(max_client, data)


    async def create_cell_for_file(self):
        root = await self._get_payload_info()
        self.url = root['url']
        self.video_id = root['videoId']
        self.token = root['token']


class File(DataBodyMixin, BaseFile):
    async def _init(self, max_client, data, filename='None'):
        self.opcode: int = Opcode.CREATE_FILE.value
        self.file_id: str = ''
        self.token: str = ''
        self.file_size: int = len(data)
        self.uploaded: bool = False
        self._set_headers(self.file_size, filename)
        await super()._init(max_client, data)


    async def create_cell_for_file(self):
        root = await self._get_payload_info()
        self.url = root['url']
        self.file_id = root['fileId']
        self.file_token = root['token']


async def qr_callback(url):
    """just blank"""
    ...


async def main():
    #Just test
    # token = os.getenv('token')
    # max_api = await MaxApi.create(qr_callback, token=token)
    # f = open('../../test_video.mp4', 'rb')
    # file = await File(max_api.max_client, f.read(), filename='test_v')
    # print(file.url)
    # # print(file.video_id)
    # # print(file.video_token)
    # f.close()
    # stime = round(time.time() * 1000)
    # print(stime)
    # response = await max_api.max_client.send_and_receive(opcode=64, payload={
    #     "chatId": -69642481385536,
    #     "message": {
    #         "cid": -stime,
    #         "attaches": [
    #             {
    #                 "_type": "FILE",
    #                 'fileId': file.file_id,
    #             }
    #         ]
    #     },
    #     "notify": True
    # })
    #
    # while response.get('payload', {}).get('error'):
    #     response = await max_api.max_client.send_and_receive(opcode=64, payload={
    #         "chatId": -69642481385536,
    #         "message": {
    #             "cid": -stime,
    #             "attaches": [
    #                 {
    #                     "_type": "FILE",
    #                     'fileId': file.file_id,
    #                 }
    #             ]
    #         },
    #         "notify": True
    #     })
    #     # await asyncio.sleep(5)
    #     # pprint(response)
    #
    # # pprint(response)
    # print(file.uploaded)
    ...


if __name__ == '__main__':
    asyncio.run(main())
