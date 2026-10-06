import enum
import unittest

from pyromax.encoding.JsonEncoding import JsonEncoding
from pyromax.encoding.MsgPack import MsgPackDictEncoding
from pyromax.encoding.NoEncoding import NoEncoding


class Kind(enum.Enum):
    VALUE = "value"


class EncodingTest(unittest.TestCase):
    def setUp(self) -> None:
        config = object()
        self.json = JsonEncoding(config)  # type: ignore[arg-type]
        self.msgpack = MsgPackDictEncoding(config)  # type: ignore[arg-type]
        self.none = NoEncoding(config)  # type: ignore[arg-type]

    def test_json_round_trip_and_dict_passthrough(self) -> None:
        value = {"text": "привет", "nested": [1, True, None]}
        encoded = self.json.encode(value)
        self.assertIsInstance(encoded, str)
        self.assertEqual(self.json.decode(encoded), value)
        self.assertIs(self.json.decode(value), value)

    def test_no_encoding_preserves_identity(self) -> None:
        value = {"mutable": []}
        self.assertIs(self.none.encode(value), value)
        self.assertIs(self.none.decode(value), value)

    def test_msgpack_round_trip_does_not_require_version(self) -> None:
        request = {
            "seq": 42,
            "opcode": 1,
            "cmd": 7,
            "payload": {"kind": Kind.VALUE, "items": (1, 2)},
        }
        packet = self.msgpack.encode(request.copy())

        self.assertEqual(len(packet) - self.msgpack.HEADER_SIZE,
                         self.msgpack.unpack_header_to_get_payload_length(packet))
        decoded = self.msgpack.decode(packet)
        self.assertEqual(decoded["seq"], 42)
        self.assertEqual(decoded["opcode"], 1)
        self.assertEqual(decoded["cmd"], 7)
        self.assertEqual(decoded["ver"], 11)
        self.assertEqual(decoded["payload"], {"kind": "value", "items": [1, 2]})

    def test_msgpack_accepts_json_input(self) -> None:
        packet = self.msgpack.encode(
            '{"seq": 2, "opcode": 3, "cmd": 4, "ver": 5, "payload": {"ok": true}}'
        )
        self.assertEqual(
            self.msgpack.decode(packet),
            {"seq": 2, "opcode": 3, "cmd": 4, "ver": 5, "payload": {"ok": True}},
        )

    def test_decode_rejects_truncated_payload(self) -> None:
        packet = self.msgpack._create_packet(1, 2, 3, 11, {"x": "y"})
        with self.assertRaisesRegex(ValueError, "payload length does not match"):
            self.msgpack.decode(packet[:-1])

    def test_safe_decompress_rejects_unknown_flag(self) -> None:
        self.assertIsNone(self.msgpack._safe_decompress(b"data", flags=0x80))
        self.assertEqual(self.msgpack._safe_decompress(b"data", flags=0), b"data")
