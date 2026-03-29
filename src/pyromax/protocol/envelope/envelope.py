import asyncio
import json
import logging
from asyncio import Event
from typing import Any, AsyncGenerator, Iterable

from src.pyromax.protocol.bases.StreamProtocol import StreamMaxProtocol
from src.pyromax.protocol.bases.methods import BaseMaxMethod
from src.pyromax.protocol.bases.request_response import Response, Request
from src.pyromax.routing.event_router import EventRouter, FutureLikeObject

from pydantic import BaseModel

from ...transtport.bases import StreamTransport


class Envelope(BaseModel, Request, Response):
    seq: int
    cmd: int = None
    opcode: int | str = None
    payload: Any


    def __hash__(self) -> int:
        return hash(f"seq:{self.seq}, opcode:{self.opcode}, cmd:{self.cmd}")


    def is_my_response(self, response: 'Envelope') -> bool:
        if not isinstance(response, Response):
            raise TypeError('response must be Response instance')
        return response.seq == self.seq and response.cmd == int(not self.cmd) and response.opcode == self.opcode


class EnvelopeProtocol(StreamMaxProtocol):
    def __init__(self, transport: StreamTransport, ping_interval=30) -> None:
        self.event_router = EventRouter()
        self.__logger = logging.getLogger('EnvelopeProtocol')
        self.__transport = transport
        self._reader_task = None
        self._ping_interval = ping_interval
        self.failed = Event()
        self.running = Event()
        self.__transport_inited = Event()


    async def _async_init(self, transport: StreamTransport, ping_interval=30) -> None:
        await asyncio.to_thread(self.__init__, transport=transport, ping_interval=ping_interval)
        await self.connect()
        self.__logger.info('websocket connected')


    async def connect(self) -> None:
        await self.__transport.connect()
        self.__logger.debug('websocket connected')
        self._reader_task = asyncio.create_task(self.receive_reader())
        self.__logger.debug('background tasks started')
        del self.event_router
        self.event_router = EventRouter()
        self.running.set()
        self.failed.clear()
        self.__transport_inited.set()


    async def close(self):
        self.__logger.debug('closing protocol')
        self.__logger.debug('terminated keepalive task')
        self._reader_task.cancel()
        self._reader_task = None
        self.__logger.debug('terminated reader task')
        await self.__transport.close()
        self.__transport_inited.clear()
        self.__logger.debug('transport closed')
        self.__logger.debug('protocol closed')
        self.running.clear()
        self.failed.clear()


    async def send(self, method: BaseMaxMethod, data: dict) -> FutureLikeObject:
        if not isinstance(data, dict):
            raise TypeError('data must be dict instance')
        envelope = await self.from_request(request=data)
        request = await method(request=envelope)
        await self.__transport_inited.wait()
        await self.__transport.send(request.model_dump(by_alias=True))
        self.__logger.debug(f'send request: {envelope}')
        return await self.event_router.create_record(envelope)


    async def receive_reader(self):
        try:
            while True:
                await self.running.wait()
                response_raw = json.loads(await self.__transport.recv())

                # from random import random
                # rnd = random()
                #
                # if rnd > 0.5:
                #     print('raise')
                #     print(f'raise {str(response_raw)[0:100]}...')
                #     raise self.__transport.BASE_EXCEPTION_FOR_TRANSPORT('test')

                response = self.from_response(response_raw)
                self.__logger.debug('fetched response %s', response)
                await self.event_router.resolve_response(response)
        except self.__transport.BASE_EXCEPTION_FOR_TRANSPORT as e:
            self.__logger.error('error occurred in reader: %s', e)
        finally:
            self.failed.set()
            self.running.clear()
            self.event_router.cancel_all()


    async def get_updates(self) -> Iterable:
        while True:
            try:
                await self.running.wait()
                updates = await self.event_router.pop_all_updates()
                break
            except asyncio.CancelledError:
                self.__logger.error('get_all_updates cancelled')
        return updates


    async def from_request(self, request: dict) -> Envelope:
        if 'seq' not in request:
            request['seq'] = await self.event_router.correlator.get_counter()
            self.event_router.correlator.counter_increment()
        if 'payload' not in request:
            request['payload'] = None
        return Envelope(**request)


    def from_response(self, data: dict) -> Envelope:
        return Envelope(**data)


# async def main():
#     logging.basicConfig(level=logging.DEBUG)
#     transport = await WebSocketTransport("wss://ws-api.oneme.ru/websocket")
#     protocol = await EnvelopeProtocol(transport=transport)
#
#     await protocol.close()
#
#
# if __name__ == '__main__':
#     asyncio.run(main())

