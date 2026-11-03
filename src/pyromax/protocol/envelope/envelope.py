from __future__ import annotations
import asyncio
import logging
from asyncio import Future
from collections.abc import Callable, Iterable
from typing import Any, cast, TYPE_CHECKING

from ..bases import StreamMaxProtocol, BaseMaxProtocolMethod, Response, Request
from ...encoding import BaseEncoding
from ...routing.event_router import EventRouter
from ...exceptions import (
    AlreadyCancelledError,
    SendingProtocolError,
    ConnectProtocolError,
    GetUpdatesProtocolError,
    BaseProtocolError,
    RoutingError,
    ConnectTransportError,
    CloseTransportError,
    CloseProtocolError,
    SendingTransportError,
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

        self.event_router: EventRouter[Envelope, Envelope] | None

        self._network_lock = asyncio.Lock()

        self._exceptions_reporter_factory: (
            Callable[[], Callable[[Exception, str], Any]] | None
        ) = None

        self._logger = logging.getLogger("EnvelopeProtocol")

        self._transport = transport
        self._reader_task: asyncio.Task[Any] | None = None

        self._encoding = encoding

    def set_error_reporter_factory(
        self,
        exceptions_reporter_factory: (
            Callable[[], Callable[[Exception, str], Any]] | None
        ),
    ) -> None:
        """Set exceptions callback."""
        self._exceptions_reporter_factory = exceptions_reporter_factory

    @property
    def _error_reporter(self) -> Callable[[Exception, str], None] | None:
        error_reporter = None
        if self._exceptions_reporter_factory is not None:
            error_reporter = self._exceptions_reporter_factory()
        return error_reporter

    async def _async_init(
        self,
        transport: StreamTransport[BaseEncoding[Any, Any, Any, Any]],
        encoding: BaseEncoding[Any, Any, Any, Any],
        extra_config: ExtraConfig,
        *args: Any,
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

        self.event_router = EventRouter[Envelope, Envelope]()
        self._logger.info("protocol connected")

    @property
    def transport(self) -> StreamTransport[BaseEncoding[Any, Any, Any, Any]]:
        """Transport.

        :returns: The using transport.
        :rtype: StreamTransport
        """
        return self._transport

    async def _close_after_connect_failure(self) -> None:
        """Clean up a partial connection without masking its original error."""
        try:
            await self._close()
        except CloseProtocolError as close_error:
            self._logger.warning(
                "Cleanup after connection failure also failed: %s",
                close_error,
            )

    async def connect(self) -> None:
        """Connect the protocol transport and start its response reader.

        :raises ConnectProtocolError: If the transport cannot be connected.


        :param current_gen: The current gen value.
        :type current_gen: int
        """
        async with self._network_lock:

            try:
                await self._close()
            except CloseProtocolError as e:
                self._logger.warning("Closing protocol error while connect: %s", e)
                raise ConnectProtocolError("Closing error") from e

            error_reporter = self._error_reporter

            try:
                await asyncio.wait_for(self._transport.connect(), timeout=30)

            except ConnectTransportError as e:
                await self._close_after_connect_failure()
                self._logger.error(
                    "Transport got connection error while connecting=%s",
                    e,
                    exc_info=True,
                )
                raise ConnectProtocolError("Transport connection error") from e
            except asyncio.TimeoutError as e:
                self._logger.error("Connection timeout")
                await self._close_after_connect_failure()
                raise ConnectProtocolError("Timeout to connect") from e
            except Exception as e:
                await self._close_after_connect_failure()
                raise ConnectProtocolError("Connect error") from e

            try:
                router = self.event_router
                if router:
                    self.event_router = None
                    await router.cancel_all()

                self.event_router = EventRouter()
                reader_task = asyncio.create_task(self.receive_reader())

                reader_task.add_done_callback(
                    lambda task: self._reader_done(task, error_reporter)
                )
                self._reader_task = reader_task
                self._logger.info("Background tasks started")

            except Exception as start_error:
                self._logger.error("Start background tasks error")
                try:
                    await self._close()
                except CloseProtocolError as close_error:
                    self._logger.warning(
                        "Closing protocol error while connect: %s", close_error
                    )
                    raise ConnectProtocolError("Closing error") from close_error
                raise ConnectProtocolError(
                    "Start background tasks error"
                ) from start_error

    async def _close(
        self,
        pending_requests_exc: Exception | None = None,
    ) -> None:
        """Close."""
        self._logger.info("Closing protocol")
        reader_task = self._reader_task
        self._reader_task = None
        if reader_task:
            try:
                reader_task.cancel()
                await asyncio.wait_for(reader_task, timeout=5)
            except asyncio.CancelledError:
                self._logger.debug("Reader already cancelled(in close)")
            except asyncio.TimeoutError:
                self._logger.warning("Reader task got stop stop timeout(in close)")
            except Exception as e:
                self._logger.error("Reader ended with exception: %s", e, exc_info=True)

        event_router = self.event_router
        if event_router:
            self.event_router = None
            await event_router.cancel_all(pending_requests_exc)

        self._logger.info("Terminated reader task")
        try:
            await asyncio.wait_for(self._transport.close(), timeout=30)
            self._logger.info("Transport closed")
            self._logger.info("Protocol closed")
        except asyncio.TimeoutError as e:
            self._logger.warning("Transport close timeout")
            raise CloseProtocolError("Transport close timeout") from e
        except CloseTransportError as e:
            self._logger.warning("Transport close error=%s", e, exc_info=True)
            raise CloseProtocolError("Transport close error") from e
        except Exception as e:
            self._logger.warning("Transport close failed")
            raise CloseProtocolError("Transport close failed") from e

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

        error_reporter = self._error_reporter

        if not isinstance(data, dict):
            raise TypeError("Data must be dict instance")
        envelope = await self.from_request(request_data=data)
        try:
            request = await method(request=envelope)
        except Exception as e:
            self._logger.exception(
                "Failed to create envelope, method: %s", method.__class__.__name__
            )
            raise SendingProtocolError("Failed to create envelope") from e

        event_router = self.event_router
        if not event_router:
            raise SendingProtocolError("No event router while send")
        try:
            record = event_router.create_record(request)
        except AlreadyCancelledError:
            raise SendingProtocolError("Event router already cancelled")

        try:
            encoded_frame = self._encoding.encode(request.model_dump(by_alias=True))
            await self._transport.send(encoded_frame)
        except SendingTransportError as e:
            self._logger.error("Transport sending error: %s", e, exc_info=True)
            try:
                if error_reporter is not None:
                    error_reporter(e, "EnvelopeProtocol.send")
            except Exception:
                self._logger.exception(
                    "Exceptions_callback failed=%s", e, exc_info=True
                )
            await event_router.cancel_request(request)
            raise SendingProtocolError("Transport sending error") from e
        except Exception as e:
            self._logger.error("Sending error=%s", e, exc_info=True)
            try:
                if error_reporter is not None:
                    error_reporter(e, "EnvelopeProtocol.send")
            except Exception:
                self._logger.exception("Exceptions_callback failed")
            await event_router.cancel_request(request)
            raise SendingProtocolError("Sending error") from e
        self._logger.debug("Send request: %s", envelope.model_dump(by_alias=True))

        return record

    def _reader_done(
        self,
        task: asyncio.Task[Any],
        error_reporter: Callable[[Exception, str], Any] | None,
    ) -> None:
        """Reader done.

        :param task: asyncio.Task[Any] instance to process.
        :type task: asyncio.Task[Any]
        :param gen: The gen value.
        :type gen: int | None
        """
        from ...utils import debug_tasks

        self._logger.debug("%s", debug_tasks())

        try:
            exc = task.exception()
        except asyncio.CancelledError:
            self._logger.warning("Reader task cancelled outer")
            return
        except Exception as e:
            self._logger.exception(
                "Failed to inspect reader task, get exception operation ended with unknown exception=%s",
                e,
                exc_info=e,
            )
            return
        except BaseException:
            raise

        if exc is not None:
            try:
                if error_reporter is not None:
                    self._logger.debug("Sending exception into exceptions callback")
                    error_reporter(
                        cast(Exception, exc), "EnvelopeProtocol.receive_reader"
                    )
            except Exception:
                self._logger.exception(
                    "Exception occurred while sending reader exception into exceptions callback"
                )

                self._logger.error(
                    "Reader unhandled exception",
                    exc_info=(type(exc), exc, exc.__traceback__),
                )

    async def receive_reader(self) -> None:
        """Receive reader.

        :raises RuntimeError: If no event router while receive.
        """
        event_router = self.event_router
        if event_router is None:
            raise RuntimeError("No event router while receive")
        while True:
            raw_data = await self._transport.recv()
            response = self._encoding.decode(raw_data)

            # from random import random
            #
            # rnd = random()
            #
            # if rnd > 0.5 and response["seq"] > 3:
            #     print("raise")
            #     print(f"raise {str(response)[0:100]}...")
            #     from ...exceptions import BaseTransportError
            #
            #     raise BaseTransportError("test")

            response = self.from_response(response)
            self._logger.debug("fetched response %s", response)
            response_resolved = await event_router.resolve_response(response)
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
            event_router = self.event_router
            if event_router is None:
                raise GetUpdatesProtocolError("No event router while receive")
            updates = await event_router.pop_all_updates()
        except (AlreadyCancelledError, RoutingError) as e:
            self._logger.error(
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
