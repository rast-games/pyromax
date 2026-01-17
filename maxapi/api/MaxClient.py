import random

from websockets import connect
from websockets.typing import Origin
from websockets.exceptions import ProtocolError


import logging
import json
import asyncio
import string

from maxapi.utils import get_random_string, NotFoundFlag
from maxapi.types import Update, Opcode


class MaxClient:
    @classmethod
    async def create_client(cls, max_api):
        self = cls(max_api)
        await self.__init()
        return self


    def __init__(self, max_api):
        self.max_api = max_api
        self.__logger: logging.Logger = logging.getLogger('MaxClient')
        self.__polling_interval: int = 0
        self.websocket: connect = None
        self.inited: bool = False
        self.__counter: int = 0
        self.sec_websocket_key: str = get_random_string(23, string.ascii_uppercase + string.digits)
        self._wait_recv = False
        self.__update_fallback = None


    @property
    def update_fallback(self):
        return self.__update_fallback

    @update_fallback.setter
    def update_fallback(self, update_fallback):
        self.__update_fallback = update_fallback

    @property
    def counter(self):
        return self.__counter


    def counter_increment(self):
        self.__counter += 1


    @property
    def polling_interval(self):
        return self.__polling_interval


    @polling_interval.setter
    def polling_interval(self, value):
        self.__polling_interval = value


    async def __init(self):
        self.__logger.info('Initializing Max WebSocket Client')
        if not self.websocket:
            self.websocket = await connect("wss://ws-api.oneme.ru/websocket",
                                     origin=Origin('https://web.max.ru'),
                                     user_agent_header='Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0',
                                           ping_interval=self.__polling_interval)
            self.inited = True

        # await use_decorator_on_obj_method(self, 'send_message', self.max_api._recreate_client_for_exception)
        # await use_decorator_on_obj_method(self, 'wait_recv', self.max_api._recreate_client_for_exception)


    async def close_websocket(self):
        if self.websocket:
            await self.websocket.close()
            self.websocket.ws_client = None
            self.max_api = None
            self.__logger.info('WebSocket Closed')
            # del self.send_message
            # del self.wait_recv

    async def send_message(self, message: dict, send_count: int = 1) -> None:
        # test = random.random()
        # print(test)


        # if test > 0.7:
        #     raise ProtocolError('Error sending message')
        for _ in range(send_count):
            await self.websocket.send(json.dumps(message))
        self.counter_increment()


    async def wait_recv(self, recv_count: int = 1, return_updates: bool = False) -> list[dict]:
        responses = []
        self._wait_recv = True
        for _ in range(recv_count):
            response = json.loads(await self.websocket.recv())
            while response['opcode'] == Opcode.PUSH_NOTIFICATION.value and not return_updates:
                if self.__update_fallback is not None:
                    await self.__update_fallback(Update(response['payload']))
                response = json.loads(await self.websocket.recv())
            responses.append(response)
        self._wait_recv = False
        return responses



    async def send_and_receive(self, ver: int = 11, opcode: int = 1, cmd: int = 0, seq: int = None, payload: dict | str = None):
        request = {
            'ver': ver,
            'opcode': opcode,
            'cmd': cmd,
        }

        if not payload == 'NotSend':
            request['payload'] = payload
        if not seq == 'NotSend':
            request['seq'] = seq if seq else self.__counter
        await self.send_message(request)

        response = await self.wait_recv()
        response = response[0]


        await asyncio.sleep(self.__polling_interval)
        return response



async def main():
    max_client = await MaxClient.create_client()

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)

    asyncio.run(main())