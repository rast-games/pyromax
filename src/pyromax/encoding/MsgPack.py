from __future__ import annotations
import json
import logging
import struct
from enum import Enum
from io import BytesIO
from typing import Any, cast, TYPE_CHECKING

import lz4.block  # type: ignore[import-untyped]
import msgpack  # type: ignore[import-untyped]

from .base import DictAndBytesEncoding
from .registry import register_encoding

if TYPE_CHECKING:
    from ..config import ExtraConfig

import zstandard


@register_encoding("MsgPackDictEncoding")
class MsgPackDictEncoding(DictAndBytesEncoding):
    """
    An encoding implementation suitable for use with the Envelope protocol and socket transport determines the size of
    the socket message header and provides an implementation for obtaining the message length from the header.
    Serializes Json data into bytes and deserializes bytes into Json.
    """

    HEADER_STRUCT = struct.Struct(">BBHHI")
    _HEADER_SIZE: int = HEADER_STRUCT.size

    def __init__(self, extra_config: ExtraConfig) -> None:
        super().__init__(extra_config)
        self._logger = logging.getLogger("MsgPackDictEncoding")

    @property
    def HEADER_SIZE(self) -> int:
        return self._HEADER_SIZE

    def encode(self, data: str | dict[Any, Any], *args: Any, **kwargs: Any) -> bytes:
        request: dict[Any, Any]
        if isinstance(data, str):
            request = json.loads(data)
        else:
            request = data

        seq = int(request.get("seq", 0))
        opcode = int(request.get("opcode", 1))
        cmd = int(request.get("cmd", 0))
        ver = int(request.get("ver", 11))
        del request["seq"]
        del request["opcode"]
        del request["cmd"]
        if "ver" in request:
            del request["ver"]
        if not ver:
            ver = 11
        packet = self._create_packet(
            seq, opcode, cmd, ver, payload=request.get("payload")
        )

        return packet

    def _unpack_header(self, data: bytes) -> tuple[int, int, int, int, int, int]:

        header_raw = data[: self.HEADER_SIZE]

        ver, cmd, seq, opcode, payload_len = self.HEADER_STRUCT.unpack_from(
            header_raw, 0
        )
        flags = (payload_len >> 24) & 0xFF

        payload_length = payload_len & 0x00FFFFFF
        return ver, cmd, seq, opcode, flags, payload_length

    def unpack_header_to_get_payload_length(self, data: bytes) -> int:
        _, _, _, _, _, payload_len = self._unpack_header(data)
        return payload_len

    def decode(self, data: bytes, *args: Any, **kwargs: Any) -> dict[Any, Any]:
        header_raw = data[: self.HEADER_SIZE]

        ver, cmd, seq, opcode, flags, payload_length = self._unpack_header(header_raw)
        if payload_length > 0:
            payload_raw = data[10:]
            if len(payload_raw) != payload_length:
                raise ValueError("payload length does not match")
        else:
            payload_raw = b""

        payload_uncompressed: bytes
        if len(payload_raw) > 0:
            try:
                decompressed = self._safe_decompress(
                    payload_raw,
                    flags=flags,
                    start_uncompressed_size=payload_length,
                )
                if decompressed is None:
                    # decompressed = b""
                    raise ValueError("Uncompressed return None")
                payload_uncompressed = decompressed

            except ValueError as e:
                raise e
            except Exception as e:
                logging.error(f"uncompressed error: {e}")
                raise ValueError(f"uncompressed error: {e}")
        else:
            payload_uncompressed = payload_raw

        if len(payload_uncompressed) > 0:
            try:
                decoded_payload = msgpack.unpackb(
                    payload_uncompressed, strict_map_key=False
                )
            except Exception as e:
                logging.error(f"unpack error: {e}")
                raise ValueError(f"unpack error: {e}")
        else:
            decoded_payload = {}

        return {
            "opcode": opcode,
            "cmd": cmd,
            "seq": seq,
            "ver": ver,
            "payload": decoded_payload,
        }

    def _decompress_zstd(self, data: bytes, max_output: int = 5 * 1024 * 1024) -> bytes:
        try:
            with zstandard.ZstdDecompressor().stream_reader(BytesIO(data)) as reader:
                result = reader.read(max_output + 1)
        except zstandard.ZstdError as e:
            raise ValueError("Zstd: failed to decompress payload") from e

        if len(result) > max_output:
            raise ValueError("Zstd: output too large")
        return result

    def _decompress_lz4(
        self,
        data: bytes,
        max_output: int = 5 * 1024 * 1024,
        start_uncompressed_size: int = 100,
        coefficient: int = 2,
        max_retries: int = 6,
    ) -> bytes | None:
        if max_output < 1 or max_retries < 1:
            return None

        # ``uncompressed_size`` controls the allocation made by python-lz4.
        # Never let retries allocate beyond the configured output limit.
        uncompressed_size = min(max(start_uncompressed_size, 1), max_output)
        for _ in range(max_retries):
            try:
                uncompressed_data = lz4.block.decompress(
                    data,
                    uncompressed_size=uncompressed_size,
                )
                if len(uncompressed_data) > max_output:
                    raise ValueError("LZ4: output too large")

                return cast(bytes, uncompressed_data)
            except lz4.block.LZ4BlockError:
                if uncompressed_size >= max_output:
                    return None

                next_size = uncompressed_size * coefficient
                if next_size <= uncompressed_size:
                    return None
                uncompressed_size = min(next_size, max_output)
        return None

    def _safe_decompress(
        self,
        data: bytes,
        flags: int = 0,
        max_output: int = 5 * 1024 * 1024,
        start_uncompressed_size: int = 100,
        coefficient: int = 2,
        max_retries: int = 6,
    ) -> bytes | None:
        """Safe decompress.

        :param data: Data what need to be decompressed.
        :type data: bytes
        :param start_uncompressed_size: The start uncompressed size value.
        :type start_uncompressed_size: int
        :param coefficient: The coefficient value.
        :type coefficient: int
        :param max_retries: The max retries value.
        :type max_retries: int
        :returns: The resulting bytes | None value.
        :rtype: bytes | None
        """
        payload_bytes: bytes | None
        if flags == 0xFF:
            try:
                payload_bytes = self._decompress_zstd(
                    data,
                    max_output=max_output,
                )
                self._logger.debug("Payload decompressed with Zstd")
            except ValueError:
                self._logger.debug("Zstd payload decompression failed", exc_info=True)
                return None
        elif flags == 0:
            payload_bytes = data
        elif 0 < flags < 0xFF:
            try:
                # For LZ4 the flag is the server-provided compression factor.
                # It may use the full byte range up to 0xFE; 0xFF is reserved
                # for Zstd.  Starting near the expected output size also lets
                # highly compressible payloads exceed the old 32x retry limit.
                expected_size = start_uncompressed_size * flags
                payload_bytes = self._decompress_lz4(
                    data,
                    max_output=max_output,
                    start_uncompressed_size=min(expected_size, max_output),
                    coefficient=coefficient,
                    max_retries=max_retries,
                )
                self._logger.debug("Payload decompressed cof=%s", flags)
            except ValueError:
                self._logger.debug(
                    "Payload decompression failed cof=%s", flags, exc_info=True
                )
                return None
        else:
            return None
        return payload_bytes
        # uncompressed_size = start_uncompressed_size
        # for _ in range(max_retries):
        #     try:
        #         uncompressed_data = lz4.block.decompress(
        #             data,
        #             uncompressed_size=uncompressed_size,
        #         )
        #         return cast(bytes, uncompressed_data)
        #     except lz4.block.LZ4BlockError:
        #         uncompressed_size *= coefficient
        # else:
        #     return None

    def _to_msgpack_value(self, value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, dict):
            return {
                self._to_msgpack_value(k): self._to_msgpack_value(v)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self._to_msgpack_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._to_msgpack_value(item) for item in value)
        return value

    def _create_packet(
        self,
        seq: int,
        opcode: int,
        cmd: int,
        ver: int,
        payload: Any,
        flags: int = 0,
    ) -> bytes:
        """Create packet.

        :param seq: The seq value.
        :type seq: int
        :param opcode: The opcode value.
        :type opcode: int
        :param cmd: The cmd value.
        :type cmd: int
        :param ver: The ver value.
        :type ver: int
        :param payload: Payload to encode, decode, or validate.
        :type payload: Any
        :returns: The resulting bytes value.
        :rtype: bytes
        """

        packed_payload = msgpack.packb(
            self._to_msgpack_value(payload), use_bin_type=True
        )
        packed_len = ((flags & 0xFF) << 24) | (len(packed_payload) & 0x00FFFFFF)

        header = self.HEADER_STRUCT.pack(
            ver,
            cmd,
            seq,
            opcode,
            packed_len,
        )

        return bytes(header + packed_payload)

        # packed_payload = msgpack.packb(payload)
        # seq_b = seq.to_bytes(2, "big")
        # cmd_b = cmd.to_bytes(1, "big")
        # opcode_b = opcode.to_bytes(2, "big")
        # ver_b = ver.to_bytes(1, "big")
        # if packed_payload is None:
        #     payload_bytes = b""
        # payload_len = len(packed_payload)
        # payload_len_b = payload_len.to_bytes(4, "big")
        # return cast(
        #     bytes, ver_b + cmd_b + seq_b + opcode_b + payload_len_b + packed_payload
        # )

    # async def _encode(self, request: dict[str, Any]) -> None:
    #     """Send.
    #
    #     :param request: Protocol request envelope to populate or send.
    #     :type request: dict[str, Any]
    #     # :raises SocketTransportSendError: If request must be a dict with keys: "seq", "opcode", and "cmd".
    #     # :raises SocketTransportSendError: If the requested action cannot be completed.
    #     """
    #     # if not isinstance(request, dict):
    #     #     raise SocketTransportSendError(
    #     #         'request must be a dict with keys: "seq", "opcode", and "cmd"'
    #     #     )
    #     seq = int(request.get("seq", 0))
    #     opcode = int(request.get("opcode", 1))
    #     cmd = int(request.get("cmd", 0))
    #     ver = int(request.get("ver", 11))
    #     del request["seq"]
    #     del request["opcode"]
    #     del request["cmd"]
    #     if "ver" in request:
    #         del request["ver"]
    #     if not ver:
    #         ver = 11
    #     packet = self._create_packet(
    #         seq, opcode, cmd, ver, payload=request.get("payload")
    #     )
