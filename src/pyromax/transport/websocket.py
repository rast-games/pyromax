import asyncio
import logging
import json
from typing import Any
from xmlrpc.client import Binary


import websockets
from websockets import Origin
from websockets.asyncio.client import ClientConnection, connect

from .bases import StreamTransport
from .registry import register_transport



# Just aliases

WebSocketClosedException = websockets.ConnectionClosed
WebSocketException = websockets.WebSocketException


@register_transport('Websocket')
class WebSocketTransport(StreamTransport):

    def __init__(
            self,
            url: str,
            origin: str='https://web.max.ru',
            user_agent_header: str='Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0'
    ) -> None:
        self.url = url
        self.origin = Origin(origin)
        self.user_agent_header = user_agent_header
        self.ws: ClientConnection | None = None
        self.__logger = logging.getLogger('WebSocketTransport')
        self.BASE_EXCEPTION_FOR_TRANSPORT = WebSocketException
        self.OTHER_EXCEPTIONS_FOR_TRANSPORT = [WebSocketClosedException]

    async def _async_init(self, url: str) -> None:
        await asyncio.to_thread(self.__init__, url=url) # type: ignore[misc]
        self.__logger.info('Initializing WebSocket Transport')

        self.__logger.info('WebSocket was initialized')
        await self.connect()
        self.__logger.info('WebSocket connected to %s', self.url)



    async def connect(self) -> None:
        self.ws = await connect(
            self.url,
            origin=self.origin,
            user_agent_header=self.user_agent_header,
        )

    async def close(self) -> None:
        if self.ws is not None:
            await self.ws.close()
            self.ws = None
            self.__logger.info('Websocket closed')
        else:
            self.__logger.info('Websocket already closed')

    async def send(self, data: Binary | str | bytes | dict[str, Any]) -> None:
        if not isinstance(data, (Binary, str, bytes, dict)):
            raise TypeError('data must be str or bytes')

        if self.ws is None:
            raise RuntimeError('You try to send before initialization connection')
        await self.ws.send(json.dumps(data))


    async def recv(self) -> Any:
        if self.ws is None:
            raise RuntimeError('You try to recv before initialization connection')
        response = await self.ws.recv()
        return response






