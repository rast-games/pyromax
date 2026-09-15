from __future__ import annotations

import asyncio
import logging
import random
import struct
from typing import Any, cast, Final, TYPE_CHECKING
import ssl
import json
from socket import gaierror

import lz4.block  # type: ignore[import-untyped]
import msgpack  # type: ignore[import-untyped]
from python_socks.async_.asyncio import Proxy

from .bases import StreamTransport
from .registry import register_transport
from ..exceptions import (
    BaseTransportError,
    ConnectionTransportError,
    ConnectTransportError,
    SendingTransportError,
    # SocketTransportError,
    # SocketTransportConnectionError,
    # SocketTransportSendError,
)
from ..encoding import SocketEncoding
from ..utils import hide_func_call

if TYPE_CHECKING:
    from ..config import ExtraConfig


CLOSE_TIMEOUT: Final = 10

@register_transport("Socket")
class SocketTransport(StreamTransport[SocketEncoding[Any, Any]]):

    BASE_EXCEPTION_FOR_TRANSPORT = BaseTransportError
    OTHER_EXCEPTIONS_FOR_TRANSPORT = [
        ConnectionTransportError,
        SendingTransportError,
    ]

    __reader: asyncio.StreamReader | None
    __writer: asyncio.StreamWriter | None
    __buffer: bytearray
    __logger: logging.Logger
    _ssl_context: ssl.SSLContext
    url: str
    port: int

    async def _async_init(
        self,
        encoding: SocketEncoding[Any, Any],
        extra_config: ExtraConfig,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Async init.

        :param url: Resource URL.
        :type url: str
        :param host: The host value.
        :type host: str
        :param port: The port value.
        :type port: int
        """
        self._encoding = encoding


        hide_func_call(type(self).__init__, self, encoding=encoding, extra_config=extra_config,)
        while True:
            try:
                # self.__reader, self.__writer = await asyncio.open_connection(
                #     self.url, self.port, ssl=self._ssl_context
                # )
                await self.connect()
                break
            # except ConnectionError as e:
            #     self.__logger.error("Connection error: %s", e)
            #     await asyncio.sleep(1)
            # except gaierror as e:
            #     self.__logger.error("Gaierror: %s", e)
            #     await asyncio.sleep(2)

            except ConnectTransportError as e:
                self.__logger.error("Connection error: %s", e)
                await asyncio.sleep(2)

    def __init__(
        self,
        encoding: SocketEncoding[Any, Any],
        extra_config: ExtraConfig,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize the socket transport."""

        from ..config import SocketTransportConfig

        self.extra_config = extra_config
        transport_config = self.extra_config.transport
        if not isinstance(transport_config, SocketTransportConfig):
            raise TypeError(
                "transport config must be an instance of SocketTransportConfig for this transport"
            )
        self.transport_config = transport_config

        self.host = self.transport_config.host
        self.port = self.transport_config.port
        self._proxy = self.transport_config.proxy
        self._use_ssl = self.transport_config.use_ssl

        self._encoding = encoding
        self.__buffer = bytearray()
        self.__logger = logging.getLogger("SocketTransport")
        self.__reader = None
        self.__writer = None
        self._ssl_context = ssl.create_default_context()

    async def send(self, request: bytes) -> None:
        """Send.

        :param request: Protocol request envelope to populate or send.
        :type request: bytes
        """
        # assert self.__writer is not None, "Writer is not initialized"
        if self.__writer is None or not self.connected:
            self.__logger.error("Socket send failed: transport is not connected")
            raise SendingTransportError("Not connected to socket")
        self.__logger.debug("Socket send bytes=%s", len(request))
        self.__writer.write(request)
        await self.__writer.drain()
        self.__logger.debug("socket request bytes=%s was send", len(request))

    async def _recv_raw(self, nbytes: int) -> bytes:
        """Recv raw.

        :param nbytes: The nbytes value.
        :type nbytes: int
        :returns: The resulting bytes value.
        :rtype: bytes
        :raises ConnectionTransportError: If graceful shutdown.
        :raises ConnectionTransportError: If the requested action cannot be completed.
        """
        # assert self.__reader is not None, "Reader is not initialized"


        if self.__reader is None:
            self.__logger.error("socket recv failed: transport is not connected")
            raise ConnectionTransportError("Not connected to socket")

        if not self.connected:
            self.__logger.error("socket recv failed: transport is not connected")
            raise ConnectionTransportError("Not connected to socket")



        loop = asyncio.get_running_loop()
        try:
            while len(self.__buffer) < nbytes:
                chunk = await self.__reader.readexactly(nbytes - len(self.__buffer))
                if chunk == b"":
                    self.__buffer.clear()
                    await self.close()
                    self.__logger.info("Server close connection with graceful shutdown")
                    raise ConnectionTransportError("Socket graceful shutdown")
                self.__buffer.extend(chunk)
            result = self.__buffer[:nbytes]
            self.__buffer = self.__buffer[nbytes:]
            return bytes(result)
        except asyncio.IncompleteReadError as e:
            await self.close()
            self.__buffer.clear()
            self.__logger.info("Server close connection with graceful shutdown(IncompleteReadError)")
            raise ConnectionTransportError("Socket graceful shutdown")
        except (ConnectionResetError, BrokenPipeError) as e:
            self.__logger.error("Socket host=%s port=%s connection broken: %s", self.host, self.port, e)
            await self.close()
            self.__buffer.clear()
            raise ConnectionTransportError(f"Connection broken: {e}")
        except Exception as e:
            # self.__buffer = bytearray()
            await self.close()
            self.__buffer.clear()
            self.__logger.error("Socket host=%s port=%s recv error: %s", self.host, self.port, e)
            raise ConnectionTransportError(f"Socket recv error: {e}")

    async def recv(self) -> Any:
        """Recv.

        :returns: The bytes of one message returned by backend.
        :rtype: Any
        :raises ConnectionTransportError: If connection broken/shutdown while receiving.
        """
        loop = asyncio.get_running_loop()
        try:
            header_raw = await self._recv_raw(self._encoding.HEADER_SIZE)
        except ConnectionTransportError as e:
            self.__logger.error("Socket recv failed while try recv message header: %s", e)
            raise ConnectionTransportError("Socket recv") from e
        payload_length = self._encoding.unpack_header_to_get_payload_length(header_raw)
        if payload_length > 0:
            try:
                payload_raw = await self._recv_raw(payload_length)
            except ConnectionTransportError as e:
                self.__logger.error("Socket recv failed while try recv message payload: %s", e)
                raise ConnectionTransportError("Socket recv") from e
        else:
            payload_raw = b""

        return header_raw + payload_raw

    async def connect(self, **kwargs: Any) -> None:
        """Connect.

        # :param kwargs: Keyword arguments forwarded to the wrapped callable.
        # :type kwargs: Any
        :raises ConnectTransportError: If handler unknown error.
        """

        self.__logger.debug("Connecting to socket host=%s port=%s ssl=%s", self.host, self.port, self._use_ssl)
        try:

            if self._proxy:
                self.__logger.debug("Connecting to socket with proxy %s.", self._proxy)
                proxy = Proxy.from_url(self._proxy)
                sock = await proxy.connect(
                    dest_host=self.host,
                    dest_port=self.port,
                )

                server_hostname = self.host if self._use_ssl else None

                self.__reader, self.__writer = await asyncio.open_connection(
                    sock=sock,
                    ssl=self._use_ssl,
                    server_hostname=server_hostname
                )

                self.__logger.debug("Connected to socket host=%s port=%s ssl=%s with proxy=%s", self._proxy)
            else:
                self.__reader, self.__writer = await asyncio.open_connection(
                    self.host,
                    self.port,
                    ssl=self._use_ssl,
                )


        except ConnectionError as e:
            self.__logger.error("OS connection error while connecting to socket host=%s port=%s: %s",self.host, self.port, e)
            raise ConnectTransportError(f"Socket os connection error: {e}") from e
        except gaierror as e:
            self.__logger.error("Socket hanndle gaierror: %s", e)
            raise ConnectTransportError(f"Socket gaierror error: {e}") from e
        except OSError as e:
            self.__logger.error("Handle unknown OSerror while connecting to socket host=%s port=%s: %s",self.host, self.port, e)
        except Exception as e:
            self.__logger.error("Socket connection error: %s", e)
            raise ConnectTransportError(f"Socket connection error: {e}") from e
        self.__logger.info("Socket connected")
        self.__logger.info(
            "Socket connected host=%s port=%s ssl=%s",
            self.host,
            self.port,
            self._use_ssl,
        )


    async def close(self) -> None:
        """Close."""
        self.__logger.debug("Closing socket connection.")
        if self.__writer:
            try:
                self.__writer.close()
                await asyncio.wait_for(self.__writer.wait_closed(), timeout=CLOSE_TIMEOUT)
            except (OSError, TimeoutError) as e:
                self.__logger.error(f"socket close without graceful shutdown(cleanly): %s", e)
                self.__writer.transport.abort()
            finally:
                self.__writer = None
                self.__reader = None
                self.__buffer.clear()
        else:
            self.__logger.debug("Socket connection already closed(socket writer already None).")
        self.__logger.info("Socket closed")

    @property
    def connected(self) -> bool:
        return bool(self.__reader and not self.__reader.at_eof())
