import random
from asyncio import Future
from typing import Any, TYPE_CHECKING
import re

from websockets import connect
from websockets.typing import Origin
from websockets.exceptions import ProtocolError, WebSocketException

import logging
import json
import asyncio
import string


from pyromax.mixins import AsyncInitializerMixin
from pyromax.utils import get_random_string, NotFoundFlag
from pyromax.types import Update, Opcode

if TYPE_CHECKING:
    from pyromax.api import MaxApi

class MaxClient(AsyncInitializerMixin):
    async def _async_init(self, max_api):
        self.__init__(max_api)
        self._recv_task = asyncio.create_task(self.infinite_recv())
        await self._init_websocket()


    def __init__(self, max_api):
        self.max_api = max_api
        self.__logger: logging.Logger = logging.getLogger('MaxClient')
        self.__polling_interval: int = 0
        self.websocket: connect = None
        self._inited: asyncio.Event = asyncio.Event()
        self.__counter: int = 0
        self.sec_websocket_key: str = get_random_string(23, string.ascii_uppercase + string.digits)
        self.__pending_requests: dict[str, list[asyncio.Future]] = {}
        self.__message_buffer: dict[str, list[dict]] = {}
        self.__running_lock = asyncio.Lock()
        self.__recv_event: asyncio.Event = asyncio.Event()
        # self.inited = asyncio.Event()
        self._recv_exception: Exception | None = None
        self._recv_task: asyncio.Task | None = None
        self._websocket_inited = asyncio.Event()

    @property
    def counter(self):
        return self.__counter


    def counter_increment(self):
        self.__counter += 1
        return self.__counter


    @property
    def polling_interval(self):
        return self.__polling_interval


    @polling_interval.setter
    def polling_interval(self, value):
        self.__polling_interval = value


    async def _init_websocket(self):
        if not self.websocket:
            self.__logger.info('Initializing Max WebSocket Client')
            self.websocket = await connect("wss://ws-api.oneme.ru/websocket",
                                     origin=Origin('https://web.max.ru'),
                                     user_agent_header='Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0',
                                           ping_interval=self.__polling_interval)
        self._websocket_inited.set()




    async def close_websocket(self):
        if self.websocket:
            await self.websocket.close()
            self.websocket.ws_client = None
            self.max_api = None
            self.__logger.info('WebSocket Closed')
        self._websocket_inited.clear()



    def receive_is_locked(self) -> bool:
        return self.__running_lock.locked()


    async def kill_pending(self):
        for requests in self.__pending_requests.values():
            for request in requests:
                request.cancel()

            if requests:
                await asyncio.gather(*requests, return_exceptions=True)


    async def infinite_recv(self):

        self.__logger.info('Starting infinite receiving')
        try:
            await self._websocket_inited.wait()
            while True:
                response = json.loads(await self.websocket.recv())

                opcode = response['opcode']
                cmd = response['cmd']
                seq = response['seq']
                request_signature = f'{cmd}{seq}{opcode}'
                handled = False

                for pattern in self.__pending_requests.copy():
                    if re.search(pattern, request_signature):
                        for request in self.__pending_requests[pattern]:
                            if not request.done():
                                request.set_result([response])
                                handled = True
                        del self.__pending_requests[pattern]
                if not handled:
                    if request_signature in self.__message_buffer:
                        self.__message_buffer[request_signature].append(response)
                    else:
                        self.__message_buffer[request_signature] = [response]

        finally:
            pass


    async def send_message(self, message: dict, send_count: int = 1) -> None | int:
        for _ in range(send_count):
            await self.websocket.send(json.dumps(message))
        return message['seq']


    async def wait_recv(self, seq: int = None, cmd = 1, opcode: int | None = None) -> list[dict]:
        loop = asyncio.get_running_loop()
        response_future = loop.create_future()

        if not opcode:
            opcode = r'[0-9]'
        if not seq:
            seq = r'[0-9]'

        pattern = f'{cmd}{seq}{opcode}'
        for request in self.__message_buffer.keys():
            if re.search(pattern, request):
                response_future.set_result(self.__message_buffer[request])
                del self.__message_buffer[request]
                return response_future.result()

        if pattern not in self.__pending_requests:
            self.__pending_requests[pattern] = [response_future]
        else:
            self.__pending_requests[pattern].append(response_future)

        if not self._recv_task or self._recv_task.done():
            if self._recv_task and self._recv_task.exception():
                raise self._recv_task.exception()
            raise ConnectionError("Websocket reader is not running")

        try:
            done, pending = await asyncio.wait(
                [response_future, self._recv_task],
                return_when=asyncio.FIRST_COMPLETED
            )


            if self._recv_task in done:
                response_future.cancel()
                exc = self._recv_task.exception()
                if exc:
                    print(type(exc), exc)
                    raise exc
                raise ConnectionError("Websocket connection closed unexpectedly")

            return response_future.result()
        finally:
            pass

    async def send_and_receive(self, ver: int = 11, opcode: int = 1, cmd: int = 0, payload: dict | str = None):
        request = {
            'ver': ver,
            'opcode': opcode,
            'cmd': cmd,
            'seq': self.counter_increment(),
        }

        if payload != 'NotSend':
            request['payload'] = payload
        seq = await self.send_message(request)

        response = await self.wait_recv(seq=seq, cmd=int(not cmd), opcode=opcode)


        await asyncio.sleep(self.__polling_interval)
        return response, seq



async def main():
    max_client = await MaxClient.create_client()

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)

    asyncio.run(main())