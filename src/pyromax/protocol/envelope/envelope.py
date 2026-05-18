from __future__ import annotations
import asyncio
import json
import logging
from asyncio import Event, Future
from collections.abc import Iterable, Callable, Awaitable
from typing import Any, cast

from ..bases import StreamMaxProtocol, BaseMaxProtocolMethod, Response, Request
from ...routing.event_router import EventRouter
from ...exceptions import AlreadyCancelledError, SendingProtocolError, ConnectProtocolError

from pydantic import BaseModel

from ...transport.bases import StreamTransport
from ..registry import register_protocol


class Envelope(BaseModel, Request['Envelope'], Response):
    seq: int
    cmd: int | None = None
    opcode: int | str | None = None
    ver: int = 11
    payload: Any



    def __hash__(self) -> int:
        return hash(f"seq:{self.seq}, opcode:{self.opcode}, cmd:{self.cmd}")


    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Envelope):
            return NotImplemented

        return (
                self.seq == other.seq
                and self.cmd == other.cmd
                and self.opcode == other.opcode
        )


    def is_my_response(self, response: Envelope) -> bool:
        if not isinstance(response, self.__class__):
            raise TypeError('response must be Response instance')
        return response.seq == self.seq and response.cmd != self.cmd and response.opcode == self.opcode



@register_protocol('EnvelopeProtocol')
class EnvelopeProtocol(StreamMaxProtocol[Envelope, Envelope]):
    def __init__(self, transport: StreamTransport, ping_interval: int = 30) -> None:
        if not isinstance(transport, StreamTransport):
            raise TypeError('transport must be StreamTransport')
        self.event_router_lock = asyncio.Lock()
        self.exceptions_callback: Callable[[Exception, int, str], Any] | None = None
        self._network_lock = asyncio.Lock()
        self.event_router: EventRouter | None = None
        self.__logger = logging.getLogger('EnvelopeProtocol')
        self.__transport = transport
        self._reader_task: asyncio.Task[Any] | None = None
        self._ping_interval = ping_interval
        self._generation_getter: Callable[..., Awaitable[int]] | None = None
        self._current_generation: int | None = None


    def set_generation_getter(self, generation_getter: Callable[..., Awaitable[int]]):
        self._generation_getter = generation_getter

    def set_exceptions_callback(self, exceptions_callback: Callable[[Exception, int, str], Any]) -> None:
        self.exceptions_callback = exceptions_callback

    async def _async_init(self, transport: StreamTransport, ping_interval: int=30) -> None:
        if not isinstance(transport, StreamTransport):
            raise TypeError('transport must be StreamTransport')

        # await asyncio.to_thread(self.__init__, transport=transport, ping_interval=ping_interval, exceptions_callback=exceptions_callback, generation_getter=generation_getter) # type: ignore[misc]
        # Reinitialize instance state after async construction.
        # We intentionally reuse __init__ to keep IDE/type-checkers
        # aware of attribute initialization.
        await asyncio.to_thread(
            self.__init__,
            transport=transport,
            ping_interval=ping_interval,
        )

        # self.__init__(
        #     transport=transport,
        #     ping_interval=ping_interval,
        #     # exceptions_callback=exceptions_callback,
        #     # generation_getter=generation_getter,
        # )

        await self.set_event_router(EventRouter[Envelope, Envelope]())
        self.__logger.info('protocol connected')


    @property
    def transport(self) -> StreamTransport:
        return self.__transport


    async def get_event_router(self) -> EventRouter | None:
        async with self.event_router_lock:
            return self.event_router


    async def set_event_router(self, event_router: EventRouter | None) -> None:
        async with self.event_router_lock:
            self.event_router = event_router


    async def connect(self, current_gen: int) -> None:
        """
        Raises
        ------
            ConnectProtocolError
        """
        async with self._network_lock:
            self._current_generation = current_gen
            self.__logger.info(f'generation updated: {current_gen}')

            reader_task = self._reader_task
            self._reader_task = None
            if reader_task:
                self.__logger.info('find another reader, closing it...')
                try:
                    reader_task.cancel()
                    await asyncio.wait_for(reader_task, timeout=5)
                except asyncio.CancelledError:
                    self.__logger.debug('reader already cancelled in connect')
                except asyncio.TimeoutError:
                    self.__logger.warning("reader task did not stop(in connect)")

            try:
                await asyncio.wait_for(self.__transport.connect(), timeout=30)
            except asyncio.TimeoutError as e:
                self.__logger.error('connection timeout')
                await self._close()
                raise ConnectProtocolError('timeout to connect') from e
            except Exception as e:
                await self._close()
                raise ConnectProtocolError('connect error') from e

            try:
                router = await self.get_event_router()
                if router:
                    await self.set_event_router(None)
                    await router.cancel_all()

                await self.set_event_router(EventRouter())
                reader_task = asyncio.create_task(self.receive_reader(gen=current_gen))
                reader_task.add_done_callback(lambda t, gen=current_gen: self._reader_done(t, gen))
                self._reader_task = reader_task
                self.__logger.info('background tasks started')

            except Exception as e:
                self.__logger.error('start background tasks error')
                await self._close()
                raise ConnectProtocolError('start background tasks error') from e


    async def _close(self) -> None:
        self.__logger.info('closing protocol')
        reader_task = self._reader_task
        self._reader_task = None
        if reader_task:
            try:
                reader_task.cancel()
                await asyncio.wait_for(reader_task, timeout=5)
            except asyncio.CancelledError:
                self.__logger.info('reader already cancelled(in close)')
            except asyncio.TimeoutError:
                self.__logger.warning("reader task did not stop")
            except Exception as e:
                self.__logger.error('reader ended with exception: %s', e, exc_info=True)
        event_router = await self.get_event_router()
        if event_router:
            await self.set_event_router(None)
            await event_router.cancel_all()

        self.__logger.info('terminated reader task')
        try:
            await asyncio.wait_for(self.__transport.close(), timeout=30)
            self.__logger.info('transport closed')
            self.__logger.info('protocol closed')
        except asyncio.TimeoutError:
            self.__logger.warning('transport close timeout')
        except Exception:
            self.__logger.warning('transport close failed')


    async def close(self) -> None:
        async with self._network_lock:
            await self._close()





    async def send(self, method: BaseMaxProtocolMethod[Envelope], data: Any | None = None) -> Future[Envelope]:
        """
        send a envelope

        Raises
        ------
            SendingProtocolError
            AlreadyCancelledError
            RuntimeError
        """

        if data is None:
            data = {}

        if not isinstance(data, dict):
            raise TypeError('data must be dict instance')
        envelope = await self.from_request(request_data=data)
        event_router = await self.get_event_router()
        gen = self._current_generation
        if gen is None:
            raise RuntimeError('protocol not connected')

        if not event_router:
            raise RuntimeError('no event router while send')
        try:
            request = await method(request=envelope)
        except Exception as e:
            self.__logger.exception('failed to create envelope, method: %s', method.__class__.__name__)
            event_router.cancel_request(envelope, gen=gen)
            raise SendingProtocolError('failed to create envelope') from e



        try:
            record = event_router.create_record(request, gen=gen)
        except AlreadyCancelledError:
            raise SendingProtocolError('event router already cancelled')



        try:
            await self.__transport.send(request.model_dump(by_alias=True))
        except self.__transport.BASE_EXCEPTION_FOR_TRANSPORT as e:
            self.__logger.error('transport sending error: %s', e, exc_info=True)
            try:
                if self.exceptions_callback is not None:
                    self.exceptions_callback(e, gen, 'send')
            except Exception:
                self.__logger.exception('exceptions_callback failed')
            event_router.cancel_request(request, gen=gen)
            raise SendingProtocolError('transport sending error') from e
        except Exception as e:
            self.__logger.error('sending error: %s', e, exc_info=True)
            try:
                if self.exceptions_callback is not None:
                    self.exceptions_callback(e, gen, 'send')
            except Exception:
                self.__logger.exception('exceptions_callback failed')
            event_router.cancel_request(request, gen=gen)
            raise SendingProtocolError('sending error') from e
        self.__logger.debug(
            'send request: %s',
            envelope.model_dump(by_alias=True)
        )

        return record


    def _reader_done(self, task: asyncio.Task[Any], gen: int | None):
        from ...utils import debug_tasks
        self.__logger.debug('%s', debug_tasks())

        try:
            exc = task.exception()
        except asyncio.CancelledError:
            self.__logger.warning('reader task cancelled outer')
            return
        except Exception:
            self.__logger.exception('failed to inspect reader task')
            return

        if exc is not None:
            try:
                if gen is not None and self.exceptions_callback is not None:
                    self.__logger.debug('sending exception into exceptions callback')
                    self.exceptions_callback(cast(Exception, exc), gen, 'reader')
            except Exception:
                self.__logger.exception('exceptions_callback failed')

            self.__logger.error(
                'Reader unhandled exception',
                exc_info=(type(exc), exc, exc.__traceback__)
            )


    async def receive_reader(self, gen: int) -> None:
        event_router = await self.get_event_router()
        if event_router is None:
            raise RuntimeError('no event router while receive')
        while True:
            response_json = await self.__transport.recv()
            response_raw = json.loads(response_json)

            # from random import random
            # rnd = random()
            #
            # if rnd > 0.5:
            #     print('raise')
            #     print(f'raise {str(response_raw)[0:100]}...')
            #     raise self.__transport.BASE_EXCEPTION_FOR_TRANSPORT('test')

            response = self.from_response(response_raw)
            self.__logger.debug('fetched response %s', response)
            await event_router.resolve_response(response, gen=gen)




    async def get_updates(self) -> Iterable[Envelope]:
        """
        get updates from event router

        Raises
        ------
            RuntimeError
        """
        try:
            event_router = await self.get_event_router()
            if event_router is None:
                raise RuntimeError('no event router while receive')
            updates = await event_router.pop_all_updates()
        except AlreadyCancelledError:
            self.__logger.error('get_all_updates cancelled')
            raise RuntimeError('get_all_updates cancelled while getting updates')
        return updates


    async def from_request(self, request_data: dict[str, Any]) -> Envelope:
        envelope_data = dict(request_data)
        if 'seq' not in envelope_data:
            event_router = await self.get_event_router()
            if not event_router:
                raise RuntimeError('no event router while parse request')
            envelope_data['seq'] = await event_router.correlator.next_counter()
        envelope_data.setdefault('payload', None)
        return Envelope(**envelope_data)


    def from_response(self, data: dict[str, Any]) -> Envelope:
        return Envelope(**data)