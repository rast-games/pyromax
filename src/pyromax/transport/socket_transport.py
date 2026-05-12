import asyncio
import logging
import random
import struct
from typing import Any, cast
import ssl
import json

import lz4.block # type: ignore[import-untyped]
import msgpack # type: ignore[import-untyped]


from .bases import StreamTransport
from .registry import register_transport
from ..exceptions import SocketTransportError, SocketTransportConnectionError, SocketTransportSendError


@register_transport('socket')
class SocketTransport(StreamTransport):

    BASE_EXCEPTION_FOR_TRANSPORT =  SocketTransportError
    OTHER_EXCEPTIONS_FOR_TRANSPORT = [SocketTransportConnectionError, SocketTransportSendError]

    __reader: asyncio.StreamReader | None
    __writer: asyncio.StreamWriter | None
    __buffer: bytearray
    __logger: logging.Logger
    _ssl_context: ssl.SSLContext
    url: str
    port: int

    async def _async_init(self, url: str = "api.oneme.ru", host: str = 'api.oneme.ru', port: int = 443) -> None:
        self.url = url
        self.port = port
        self.__buffer = bytearray()
        self.__logger = logging.getLogger('SocketTransport')
        await asyncio.to_thread(self.__init__) # type: ignore[misc]
        self.__reader, self.__writer = await asyncio.open_connection(self.url, self.port, ssl=self._ssl_context)


    def __init__(self) -> None:
        self.__reader = None
        self.__writer = None
        self._ssl_context = ssl.create_default_context()


    async def send(self, request: bytes) -> None:
        assert self.__writer is not None, "Writer is not initialized"
        self.__writer.write(request)
        await self.__writer.drain()


    async def _recv_raw(self, nbytes: int) -> bytes:
        assert self.__reader is not None, "Reader is not initialized"

        loop = asyncio.get_running_loop()
        try:
            while len(self.__buffer) < nbytes:
                chunk = await self.__reader.readexactly(nbytes - len(self.__buffer))
                if chunk == b'':
                    self.__buffer.clear()
                    await self.close()
                    self.__logger.info('Server close connection with graceful shutdown')
                    raise SocketTransportConnectionError('graceful shutdown')
                self.__buffer.extend(chunk)
            result = self.__buffer[:nbytes]
            self.__buffer = self.__buffer[nbytes:]
            return bytes(result)
        except asyncio.IncompleteReadError as e:
            self.__buffer.clear()
            await self.close()
            self.__logger.info('Server close connection with graceful shutdown')
            raise SocketTransportConnectionError('graceful shutdown')
        except (ConnectionResetError, BrokenPipeError) as e:
            self.__logger.error('Socket connection broken: %s', e)
            await self.close()
            self.__buffer.clear()
            raise SocketTransportConnectionError(f'Connection broken: {e}')
        except Exception as e:
            self.__buffer = bytearray()
            await self.close()
            self.__logger.error('Socket recv error: %s', e)
            raise SocketTransportConnectionError(f'Socket recv error: {e}')


    def _safe_decompress(self, data: bytes, start_uncompressed_size: int = 100, coefficient: int = 2, max_retries: int = 6) -> bytes | None:
        uncompressed_size = start_uncompressed_size
        for _ in range(max_retries):
            try:
                uncompressed_data = lz4.block.decompress(data, uncompressed_size=uncompressed_size)
                return cast(bytes, uncompressed_data)
            except lz4.block.LZ4BlockError:
                uncompressed_size *= coefficient
        else:
            return None


    async def recv(self) -> Any:
        loop = asyncio.get_running_loop()

        header_raw = await self._recv_raw(10)
        ver, cmd, seq, opcode, cof, payload_len = struct.unpack(">BBHHB3s", header_raw)
        payload_length = int.from_bytes(payload_len, "big")
        if payload_length > 0:
            payload_raw = await self._recv_raw(payload_length)
        else:
            payload_raw = b''

        payload_uncompressed: bytes
        if cof > 0 and len(payload_raw) > 0:
            try:
                decompressed = self._safe_decompress(payload_raw, start_uncompressed_size=payload_length)
                if decompressed is None:
                    raise SocketTransportError('Uncompressed return None')
                payload_uncompressed = decompressed
            except Exception as e:
                logging.error(f'uncompressed error: {e}')
                raise SocketTransportError(f'uncompressed error: {e}')
        else:
            payload_uncompressed = payload_raw

        if len(payload_raw) > 0:
            try:
                decoded_payload = msgpack.unpackb(payload_uncompressed, strict_map_key=False)
            except Exception as e:
                logging.error(f'unpack error: {e}')
                raise SocketTransportError(f'unpack error: {e}')
        else:
            decoded_payload = {}

        return json.dumps(
            {
                'opcode': opcode,
                'cmd': cmd,
                'seq': seq,
                'ver': ver,
                'payload': decoded_payload,
            },
            default=bytes.hex
        )


    async def connect(self) -> None:
        self.__reader, self.__writer = await asyncio.open_connection(self.url, self.port, ssl=self._ssl_context)
        self.__logger.info('Socket connected')

    async def close(self) -> None:
        if self.__writer:
            try:
                self.__writer.close()
                await self.__writer.wait_closed()
            except Exception as e:
                self.__logger.error(f"Error while closing socket: {e}")
            finally:
                self.__writer = None
                self.__reader = None
                self.__buffer.clear()
        self.__logger.info('Socket closed')


@register_transport('socket_envelope')
class SocketTransportEnvelope(SocketTransport):

    def _create_packet(self, seq: int, opcode: int, cmd: int, ver: int, payload: Any) -> bytes:
        packed_payload = msgpack.packb(payload)
        seq_b = seq.to_bytes(1, 'big')
        cmd_b = cmd.to_bytes(2, 'big')
        opcode_b = opcode.to_bytes(2, 'big')
        ver_b = ver.to_bytes(1, 'big')
        if packed_payload is None:
            payload_bytes = b""
        payload_len = len(packed_payload)
        payload_len_b = payload_len.to_bytes(4, "big")
        return cast(bytes, ver_b + cmd_b + seq_b + opcode_b + payload_len_b + packed_payload)


    async def send(self, request: dict[str, Any]) -> None: # type: ignore[override]
        if not isinstance(request, dict):
            raise SocketTransportSendError('request must be a dict with keys: "seq", "opcode", and "cmd"')
        seq = int(request.get('seq'), 0)
        opcode = int(request.get('opcode'), 1)
        cmd = int(request.get('cmd'), 0)
        ver = int(request.get('ver'), 11)
        del request['seq']
        del request['opcode']
        del request['cmd']
        if 'ver' in request:
            del request['ver']
        if not ver:
            ver = 11
        packet = self._create_packet(seq, opcode, cmd, ver, payload=request.get('payload'))

        try:
            await super().send(packet)
        except Exception as e:
            await self.close()
            raise SocketTransportSendError(f'send error: {e}')


    async def recv(self) -> Any:
        return await super().recv()


    async def close(self) -> None:
        await super().close()


    async def connect(self) -> None:
        await super().connect()


    async def _async_init(self, *args: Any, **kwargs: Any) -> Any:
        return await super()._async_init(*args, **kwargs)
