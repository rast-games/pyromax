import asyncio
import logging
import json
from xmlrpc.client import Binary


import websockets
from websockets import Origin


from .bases import StreamTransport
from .registry import register_transport



# Just aliases

WebSocketClosedException = websockets.ConnectionClosed
WebSocketException = websockets.WebSocketException


@register_transport('Websocket')
class WebSocketTransport(StreamTransport):

    def __init__(
            self,
            url,
            origin='https://web.max.ru',
            user_agent_header='Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0'
    ):
        self.url = url
        self.origin = Origin(origin)
        self.user_agent_header = user_agent_header
        self.ws = None
        self.__logger = logging.getLogger('WebSocketTransport')
        self.BASE_EXCEPTION_FOR_TRANSPORT = WebSocketException
        self.OTHER_EXCEPTIONS_FOR_TRANSPORT = [WebSocketClosedException]

    async def _async_init(self, url):
        await asyncio.to_thread(self.__init__, url=url)
        self.__logger.info('Initializing WebSocket Transport')

        self.__logger.info('WebSocket was initialized')
        await self.connect()
        self.__logger.info('WebSocket connected to %s', self.url)



    async def connect(self):
        self.ws = await websockets.connect(
            self.url,
            origin=self.origin,
            user_agent_header=self.user_agent_header,
        )

    async def close(self):
        if self.ws is not None:
            await self.ws.close()
            self.ws = None
            self.__logger.info('Websocket closed')
        else:
            self.__logger.info('Websocket already closed')

    async def send(self, data) -> None:
        if not isinstance(data, (Binary, str, bytes, dict)):
            raise TypeError('data must be str or bytes')
        await self.ws.send(json.dumps(data))


    async def recv(self) -> dict:
        response = await self.ws.recv()
        return response






