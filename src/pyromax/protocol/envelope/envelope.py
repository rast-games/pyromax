from __future__ import annotations
import asyncio
import logging
from asyncio import Future
from collections.abc import Iterable, Callable, Awaitable
from typing import Any, cast, TYPE_CHECKING

from ..bases import StreamMaxProtocol, BaseMaxProtocolMethod, Response, Request
from ...encoding import BaseEncoding
from ...routing.event_router import EventRouter
from ...exceptions import (
    AlreadyCancelledError,
    SendingProtocolError,
    ConnectProtocolError,
    BaseTransportError,
    GetUpdatesProtocolError,
    BaseProtocolError,
    RoutingError,
)

from pydantic import BaseModel

from ...transport.bases import StreamTransport
from ..registry import register_protocol
from ...utils import hide_func_call

if TYPE_CHECKING:
    from ...config import ExtraConfig


class Envelope(BaseModel, Request["Envelope"], Response):
    seq: int
    cmd: int | None = None
    opcode: int | str | None = None
    ver: int = 11
    payload: Any

    def __hash__(self) -> int:
        """Hash.

        :returns: The resulting int value.
        :rtype: int
        """
        return hash(f"seq:{self.seq}, opcode:{self.opcode}, cmd:{self.cmd}")

    def __eq__(self, other: object) -> bool:
        """Eq.

        :param other: object instance to process.
        :type other: object
        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        """
        if not isinstance(other, Envelope):
            return NotImplemented

        return (
            self.seq == other.seq
            and self.cmd == other.cmd
            and self.opcode == other.opcode
        )

    def is_my_response(self, response: Envelope) -> bool:
        """Return whether my response.

        :param response: Protocol response to process.
        :type response: Envelope
        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        :raises TypeError: If response must be Response instance.
        """
        if not isinstance(response, self.__class__):
            raise TypeError("response must be Response instance")
        return (
            response.seq == self.seq
            and response.cmd != self.cmd
            and response.opcode == self.opcode
        )


@register_protocol("EnvelopeProtocol")
class EnvelopeProtocol(
    StreamMaxProtocol[
        Envelope, Envelope, StreamTransport[BaseEncoding[Any, Any, Any, Any]]
    ]
):
    def __init__(
        self,
        transport: StreamTransport[BaseEncoding[Any, Any, Any, Any]],
        encoding: BaseEncoding[Any, Any, Any, Any],
        extra_config: ExtraConfig,
    ) -> None:
        """Initialize the envelope protocol.

        :param transport: Transport instance.
        :type transport: StreamTransport
        # :param ping_interval: The ping interval value.
        # :type ping_interval: int
        :raises TypeError: If transport must be StreamTransport.
        """
        if not isinstance(transport, StreamTransport):
            raise TypeError("transport must be StreamTransport")
        self.event_router_lock = asyncio.Lock()
        self.exceptions_callback: Callable[[Exception, int, str], Any] | None = None
        self._network_lock = asyncio.Lock()
        self.event_router: EventRouter[Envelope, Envelope] | None = None
        self.__logger = logging.getLogger("EnvelopeProtocol")
        self.__transport = transport
        self._reader_task: asyncio.Task[Any] | None = None
        # self._ping_interval = ping_interval
        self._generation_getter: Callable[..., Awaitable[int]] | None = None
        self._current_generation: int | None = None
        self._encoding = encoding

    def set_generation_getter(
        self, generation_getter: Callable[..., Awaitable[int]] | None
    ) -> None:
        """Set generation getter.

        :param generation_getter: Callable to invoke.
        :type generation_getter: Callable[..., Awaitable[int]]
        """
        self._generation_getter = generation_getter

    def set_exceptions_callback(
        self, exceptions_callback: Callable[[Exception, int, str], Any] | None
    ) -> None:
        """Set exceptions callback.

        :param exceptions_callback: Callable to invoke.
        :type exceptions_callback: Callable[[Exception, int, str], Any]
        """
        self.exceptions_callback = exceptions_callback

    async def _async_init(
        self,
        transport: StreamTransport[BaseEncoding[Any, Any, Any, Any]],
        encoding: BaseEncoding[Any, Any, Any, Any],
        extra_config: ExtraConfig,
        *args: Any,
        # ping_interval: int = 30,
        **kwargs: Any,
    ) -> None:
        """Async init.

        :param transport: Transport backend or transport instance.
        :type transport: StreamTransport
        # :param ping_interval: The ping interval value.
        # :type ping_interval: int
        :raises TypeError: If transport must be StreamTransport.
        """
        if not isinstance(transport, StreamTransport):
            raise TypeError("transport must be StreamTransport")

        # await asyncio.to_thread(self.__init__, transport=transport, ping_interval=ping_interval, exceptions_callback=exceptions_callback, generation_getter=generation_getter) # type: ignore[misc]
        # Reinitialize instance state after async construction.
        # We intentionally reuse __init__ to keep IDE/type-checkers
        # aware of attribute initialization.
        hide_func_call(
            type(self).__init__,
            self,
            transport=transport,
            encoding=encoding,
            extra_config=extra_config,
        )

        # await self.set_event_router(EventRouter[Envelope, Envelope]())
        self.event_router = EventRouter[Envelope, Envelope]()
        self.__logger.info("protocol connected")

    @property
    def transport(self) -> StreamTransport[BaseEncoding[Any, Any, Any, Any]]:
        """Transport.

        :returns: The using transport.
        :rtype: StreamTransport
        """
        return self.__transport

    # async def get_event_router(self) -> EventRouter[Envelope, Envelope] | None:
    #     """Retrieve event router.
    #
    #     :returns: The envelope populated with the request opcode and payload.
    #     :rtype: EventRouter[Envelope, Envelope] | None
    #     """
    #     async with self.event_router_lock:
    #         return self.event_router
    #
    # async def set_event_router(
    #     self, event_router: EventRouter[Envelope, Envelope] | None
    # ) -> None:
    #     """Set event router.
    #
    #     :param event_router: EventRouter[Envelope, Envelope] instance to process.
    #     :type event_router: EventRouter[Envelope, Envelope] | None
    #     """
    #     async with self.event_router_lock:
    #         self.event_router = event_router

    async def connect(self, current_gen: int) -> None:
        """Connect the protocol transport and start its response reader.

        :raises ConnectProtocolError: If the transport cannot be connected.


        :param current_gen: The current gen value.
        :type current_gen: int
        """
        async with self._network_lock:
            self._current_generation = current_gen
            self.__logger.info(f"Protocol generation updated, current: {current_gen}")

            await self._close()
            # reader_task = self._reader_task
            # self._reader_task = None
            # if reader_task:
            #     self.__logger.info("Find another reader, closing it...")
            #     try:
            #         reader_task.cancel()
            #         await asyncio.wait_for(reader_task, timeout=5)
            #     except asyncio.CancelledError:
            #         self.__logger.debug("reader already cancelled in another place")
            #     except asyncio.TimeoutError:
            #         self.__logger.warning("reader task got stop stop timeout(in connect)")
            #     except Exception as e:
            #         self.__logger.error("reader task ended with exception=%s", e)
            #         await self._close()
            #         raise ConnectProtocolError(
            #             "reader task ended with exception"
            #         ) from e

            try:
                await asyncio.wait_for(self.__transport.connect(), timeout=30)
            except asyncio.TimeoutError as e:
                self.__logger.error("connection timeout")
                await self._close()
                raise ConnectProtocolError("timeout to connect") from e
            except Exception as e:
                await self._close()
                raise ConnectProtocolError("connect error") from e

            try:
                # router = await self.get_event_router()
                router = self.event_router
                if router:
                    # await self.set_event_router(None)
                    self.event_router = None
                    await router.cancel_all()

                # await self.set_event_router(EventRouter())
                self.event_router = EventRouter()
                reader_task = asyncio.create_task(self.receive_reader(gen=current_gen))

                def reader_done_callback_wrapper(
                    t: asyncio.Task[Any], gen: int = current_gen
                ) -> None:
                    """Wrap additional args in wrapper.

                    :param t: asyncio.Task[Any] instance to process.
                    :type t: asyncio.Task[Any]
                    :param gen: The gen value.
                    :type gen: int
                    """
                    self._reader_done(t, gen)

                reader_task.add_done_callback(reader_done_callback_wrapper)
                self._reader_task = reader_task
                self.__logger.info("Background tasks started")

            except Exception as e:
                self.__logger.error("start background tasks error")
                await self._close()
                raise ConnectProtocolError("start background tasks error") from e

    async def _close(
        self,
        pending_requests_exc: Exception | None = None,
    ) -> None:
        """Close."""
        self.__logger.info("closing protocol")
        reader_task = self._reader_task
        self._reader_task = None
        if reader_task:
            try:
                reader_task.cancel()
                await asyncio.wait_for(reader_task, timeout=5)
            except asyncio.CancelledError:
                self.__logger.debug("reader already cancelled(in close)")
            except asyncio.TimeoutError:
                self.__logger.warning("reader task got stop stop timeout(in close)")
            except Exception as e:
                self.__logger.error("reader ended with exception: %s", e, exc_info=True)
        # event_router = await self.get_event_router()
        event_router = self.event_router
        if event_router:
            # await self.set_event_router(None)
            self.event_router = None
            await event_router.cancel_all(pending_requests_exc)

        self.__logger.info("terminated reader task")
        try:
            await asyncio.wait_for(self.__transport.close(), timeout=30)
            self.__logger.info("transport closed")
            self.__logger.info("protocol closed")
        except asyncio.TimeoutError:
            self.__logger.warning("transport close timeout")
        except Exception:
            self.__logger.warning("transport close failed")

    async def close(
        self,
        pending_requests_exc: Exception | None = None,
    ) -> None:
        """Close."""
        async with self._network_lock:
            await self._close(pending_requests_exc)

    async def send(
        self, method: BaseMaxProtocolMethod[Envelope], data: Any | None = None
    ) -> Future[Envelope]:
        """send a envelope

        :raises SendingProtocolError: If the operation fails.
        # :raises AlreadyCancelledError: If the operation fails.
        :raises SendingProtocolError: If you try to send something before protocol init(event router is None).

        :param method: BaseMaxProtocolMethod[Envelope] instance to process.
        :type method: BaseMaxProtocolMethod[Envelope]
        :param data: Contextual data passed through the processing pipeline.
        :type data: Any | None
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Future[Envelope]
        :raises TypeError: If data must be dict instance.
        """

        if data is None:
            data = {}

        if not isinstance(data, dict):
            raise TypeError("data must be dict instance")
        envelope = await self.from_request(request_data=data)
        try:
            request = await method(request=envelope)
        except Exception as e:
            self.__logger.exception(
                "failed to create envelope, method: %s", method.__class__.__name__
            )
            raise SendingProtocolError("failed to create envelope") from e
        # event_router = await self.get_event_router()
        event_router = self.event_router
        if not event_router:
            raise SendingProtocolError("no event router while send")
        gen = self._current_generation
        if gen is None:
            raise SendingProtocolError("protocol not connected")
        try:
            record = event_router.create_record(request, gen=gen)
        except AlreadyCancelledError:
            raise SendingProtocolError("event router already cancelled")

        try:
            encoded_frame = self._encoding.encode(request.model_dump(by_alias=True))
            await self.__transport.send(encoded_frame)
        except BaseTransportError as e:
            self.__logger.error("transport sending error: %s", e, exc_info=True)
            try:
                if self.exceptions_callback is not None:
                    self.exceptions_callback(e, gen, "send")
            except Exception:
                self.__logger.exception("exceptions_callback failed")
            event_router.cancel_request(request, gen=gen)
            raise SendingProtocolError("transport sending error") from e
        except Exception as e:
            self.__logger.error("sending error: %s", e, exc_info=True)
            try:
                if self.exceptions_callback is not None:
                    self.exceptions_callback(e, gen, "send")
            except Exception:
                self.__logger.exception("exceptions_callback failed")
            event_router.cancel_request(request, gen=gen)
            raise SendingProtocolError("sending error") from e
        self.__logger.debug("send request: %s", envelope.model_dump(by_alias=True))

        return record

    def _reader_done(self, task: asyncio.Task[Any], gen: int | None) -> None:
        """Reader done.

        :param task: asyncio.Task[Any] instance to process.
        :type task: asyncio.Task[Any]
        :param gen: The gen value.
        :type gen: int | None
        """
        from ...utils import debug_tasks

        self.__logger.debug("%s", debug_tasks())

        try:
            exc = task.exception()
        except asyncio.CancelledError:
            self.__logger.warning("Reader task cancelled outer")
            return
        except Exception as e:
            self.__logger.exception(
                "Failed to inspect reader task, get exception operation ended with unknown exception=%s",
                e,
                exc_info=e,
            )
            return
        except BaseException:
            raise

        if exc is not None:
            try:
                if gen is not None and self.exceptions_callback is not None:
                    self.__logger.debug("sending exception into exceptions callback")
                    self.exceptions_callback(cast(Exception, exc), gen, "reader")
            except Exception:
                self.__logger.exception(
                    "Exception occurred while sending reader exception into exceptions callback"
                )

                self.__logger.error(
                    "Reader unhandled exception",
                    exc_info=(type(exc), exc, exc.__traceback__),
                )

    async def receive_reader(self, gen: int) -> None:
        """Receive reader.

        :param gen: The gen value.
        :type gen: int
        :raises RuntimeError: If no event router while receive.
        """
        # event_router = await self.get_event_router()
        event_router = self.event_router
        if event_router is None:
            raise RuntimeError("no event router while receive")
        while True:
            raw_data = await self.__transport.recv()
            response = self._encoding.decode(raw_data)

            # from random import random
            #
            # rnd = random()
            #
            # if rnd > 0.5:
            #     print("raise")
            #     print(f"raise {str(response)[0:100]}...")
            #     raise BaseTransportError("test")

            response = self.from_response(response)
            self.__logger.debug("fetched response %s", response)
            response_resolved = await event_router.resolve_response(response, gen=gen)
            if response_resolved:
                # Let the request coroutine consume a delivered response before
                # reading again.  Some API errors are immediately followed by a
                # server-side socket close; without this hand-off the lifecycle
                # observer can cancel the request and mask the domain error with
                # a generic transport failure.
                await asyncio.sleep(0)

    async def get_updates(self) -> Iterable[Envelope]:
        """get updates from event router

        :raises GetUpdatesProtocolError: If the operation fails.

        :returns: The envelope populated with the request opcode and payload.
        :rtype: Iterable[Envelope]
        """
        try:
            # event_router = await self.get_event_router()
            event_router = self.event_router
            if event_router is None:
                raise GetUpdatesProtocolError("no event router while receive")
            updates = await event_router.pop_all_updates()
        except (AlreadyCancelledError, RoutingError) as e:
            self.__logger.error(
                "get_all_updates end with exception=%s", e, exc_info=True
            )
            raise GetUpdatesProtocolError(
                "get_all_updates end with exception while getting updates"
            ) from e
        return updates

    async def from_request(self, request_data: dict[str, Any]) -> Envelope:
        """From request.

        :param request_data: dict[str, Any] instance to process.
        :type request_data: dict[str, Any]
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        :raises BaseProtocolError: If no event router while parse request.
        """
        envelope_data = dict(request_data)
        if "seq" not in envelope_data:
            # event_router = await self.get_event_router()
            event_router = self.event_router
            if not event_router:
                raise BaseProtocolError("no event router while parse request")
            envelope_data["seq"] = await event_router.correlator.next_counter()
        envelope_data.setdefault("payload", None)
        return Envelope(**envelope_data)

    def from_response(self, data: dict[str, Any]) -> Envelope:
        """From response.

        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[str, Any]
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        return Envelope(**data)
