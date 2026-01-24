import asyncio
import logging
import time
import string
from typing import List


from websockets.exceptions import ConnectionClosedOK, WebSocketException


from maxapi.utils import get_random_string
from maxapi.utils import get_dict_value_by_path
from maxapi.api import MaxClient
from maxapi.types import Chat, Opcode, Video, File, Photo
from maxapi.exceptions import LoggingError, LoggingTimeoutError, SendMessageError, SendMessageFileError
from maxapi.mixins import AsyncInitializerMixin


# pprint(dir(Connection))


class MaxApi(AsyncInitializerMixin):
    # @classmethod
    # async def create(cls, url_callback, device_id: str = None, token: str = None):
    #     self = cls(device_id, token)
    #     await self.attach()
    #     await self.login(url_callback)
    #     await self._authorize()
    #     return self

    async def _init(self, url_callback, device_id: str = None, token: str = None):
        self.__init__(device_id, token)
        await self.attach()
        await self.login(url_callback)
        await self._authorize()


    async def reload_if_connection_broke(self, dispatcher):
        while True:
            try:
                await dispatcher.start_polling(self)
            except WebSocketException:
                self.__logger.warning('WebSocket connection broke')
                await self.detach()
                await self.attach()
                await self.send_user_agent()
                await self._authorize()

    # async def _recreate_client_for_exception(self, method):
    #     async def wrapper(*args, **kwargs):
    #         while True:
    #             try:
    #                 return await  method(*args, **kwargs)
    # 
    #             except WebSocketException as e:
    #                 self.__logger.info('connection closed by websocket exception %s, reconnecting', e)
    #                 await self.detach()
    #                 await self.attach()
    #                 await self._authorize()
    #     return wrapper





    def __init__(self, device_id: str = None, token: str = None):
        self.max_client: MaxClient | None = None
        self._polling_interval: int = 5
        self._track_id: int | None = None
        self.first_name: str | None = None
        self.last_name: str | None = None
        self.name: str | None = None
        self.type: str | None = None
        self.phone: str | None = None
        self.update_time: int | None = None
        self.id: int | None = None
        self.account_status: str | None = None
        self.__logger: logging.Logger = logging.getLogger('MaxApi')
        self.chats: list[Chat] | None = None
        self.start_time = time.time()
        self.__token = token if token else None
        self.device_id = device_id if device_id else self.get_random_device_id()
        self.client_is_login: bool = True if self.__token else False


    async def attach(self) -> None:
        if not self.max_client:
            self.max_client = await MaxClient.create_client(self)
            self.start_time = time.time()

    async def detach(self):
        if self.max_client:
            await self.max_client.close_websocket()
            self.max_client = None
        return self.__token, self.device_id, self._polling_interval


    @staticmethod
    def get_random_device_id():
        random_string = list(get_random_string(32, string.ascii_lowercase + string.digits))

        for inx in [8, 13, 18, 23]:
            random_string.insert(inx, '-')

        return ''.join(random_string)


    async def send_user_agent(self) -> tuple[int, int, int, str] | None:
        await self.max_client.send_and_receive(opcode=6, payload={
            "userAgent": {"deviceType": "WEB", "locale": "ru", "deviceLocale": "ru", "osVersion": "Alpha",
                          "deviceName": "MaxBot",
                          "headerUserAgent": 'Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0',
                          "appVersion": "25.12.14", "screen": "1440x2560 1.0x", "timezone": "Europe/Moscow"},
            "deviceId": self.device_id},)

        if self.client_is_login:
            return

        response = await self.max_client.send_and_receive(opcode=Opcode.METADATA_FOR_LOGIN.value, payload='NotSend')

        polling_interval = response['payload']['pollingInterval'] / 1000
        track_id = response['payload']['trackId']
        expires_at = response['payload']['expiresAt'] / 1000
        url = response['payload']['qrLink']

        return polling_interval, track_id, expires_at, url


    async def login(self, url_callback):
            try:
                # if not self.max_client:
                #     raise LoggingError('dont construct object, use MaxApi.create() method')


                self.__logger.info('Start Login')

                try:
                    metadata = await self.send_user_agent()

                    if metadata:
                        self._polling_interval, self._track_id, expires_at, url = metadata
                    else:
                        return True
                    # self.__logger.info('got metadata')
                except KeyError:
                    self.__logger.error('Not found attributes in json')
                    raise LoggingError('Not found attributes in json')
                self.max_client.websocket.ping_interval = self._polling_interval

                await asyncio.create_task(url_callback(url))

                try:
                    async with asyncio.timeout(expires_at - time.time()):
                        while not self.client_is_login:
                            response = await self.max_client.send_and_receive(opcode=Opcode.TRACK_LOGIN.value, payload={"trackId": self._track_id})
                            if get_dict_value_by_path('payload status loginAvailable', response) == True:
                                self.__logger.info('Login Successful')
                                self.client_is_login = True
                                break
                            await asyncio.sleep(self._polling_interval)
                except asyncio.TimeoutError:
                    self.__logger.error('Login Timeout')
                    raise LoggingTimeoutError('Login Timeout')
                await self._get_user_data()

                return True
            except ConnectionClosedOK:
                self.__logger.info('Login Failed')
                raise LoggingError('Connection closed')


    async def _get_user_data(self) -> None:
        self.__logger.info('Getting User Data...')
        response = await self.max_client.send_and_receive(opcode=Opcode.GET_USER_DATA.value, payload={'trackId': self._track_id})
        self.__token = response['payload']['tokenAttrs']['LOGIN']['token']
        self.id = response['payload']['profile']['contact']['id']
        self.name = response['payload']['profile']['contact']['names'][0]['name']
        self.first_name = response['payload']['profile']['contact']['names'][0]['firstName']
        self.last_name = response['payload']['profile']['contact']['names'][0]['lastName']
        self.type = response['payload']['profile']['contact']['names'][0]['type']
        self.phone = response['payload']['profile']['contact']['phone']
        self.update_time = response['payload']['profile']['contact']['updateTime']

    async def _authorize(self) -> None:
        self.__logger.info('Sending authorize request...')
        response = await self.max_client.send_and_receive(opcode=Opcode.AUTHORIZE.value, payload = {
            'interactive': False,
            'token': self.__token,
        })


        await self.max_client.wait_recv()


        data = response['payload']['chats']
        chats = []

        for json_chat in data:
            chats.append(Chat(json_chat, self.max_client))
        self.chats = chats
        self.__logger.info('Authorized')


    async def get_chat_per_id(self, chat_id: int):
        self.__logger.info('Getting chat info...')
        response = await self.max_client.send_and_receive(opcode=Opcode.GET_CHAT.value, payload={
            'chatIds': [chat_id],
        })

        self.__logger.info('Got chat info')
        return Chat(response['payload']['chats'][0], self.max_client, id=chat_id)

    async def send_message(self, chat_id, text, attaches: List[Video | File | Photo] = [], file_id_test=0):
        types_of_attachments = {
            Video: 'VIDEO',
            File: 'FILE',
            Photo: 'PHOTO',
        }

        required_params_for_type = {
            'VIDEO': (('videoId', 'video_id'), ('token',)),
            'FILE': (('fileId', 'file_id'),),
            'PHOTO': (('photoToken', 'photo_token'),),
        }

        loaded_attachments = []
        for attachment in attaches:
            type_of_attachment = types_of_attachments[type(attachment)]

            payload = {
                '_type': type_of_attachment,
            }

            for param in required_params_for_type[type_of_attachment]:
                if len(param) == 1:
                    payload[param[0]] = getattr(attachment, param[0])
                elif len(param) == 2:
                    payload[param[0]] = getattr(attachment, param[1])

            loaded_attachments.append(payload)

        payload = {
            'chatId': chat_id,
            'message': {
                'cid': -round(time.time() * 1000),
                'attaches': loaded_attachments,
            },
        }
        if text:
            payload['message']['text'] = text

        response = await self.max_client.send_and_receive(opcode=Opcode.SEND_MESSAGE.value, payload=payload)
        while error_if_exist := get_dict_value_by_path('payload error', response):
            error_message = get_dict_value_by_path("payload message", response)
            match error_if_exist:
                case 'attachment.not.ready':
                    response = await self.max_client.send_and_receive(opcode=Opcode.SEND_MESSAGE.value, payload=payload)
                    continue
                case 'proto.payload':
                    raise SendMessageFileError(
                        f'''
                        error: {error_if_exist},
                        message: {error_message}
                        '''
                    )
                case _:
                    raise SendMessageError(
                        f'''
                        error: {error_if_exist},
                        message: {error_message}
                        '''
                    )





async def main():
    logging.basicConfig(level=logging.INFO)



    # max_api = await MaxApi.create()


    # chat = await max_api.get_chat_per_id(-69642481385536)
    # messages = [(inx + 1, message.text, message.attaches) for inx, message in enumerate(await chat.get_all_messages(chat.last_message.time))]
    # pprint(messages)
    #
    # await max_api.max_client.close_websocket()






if __name__ == '__main__':
    asyncio.run(main())