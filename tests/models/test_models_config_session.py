import unittest

from pyromax.config import ExtraConfig, SocketTransportConfig, WebSocketTransportConfig
from pyromax.models.Message import Message
from pyromax.models.Session import SessionInfo, SyncOverrides, SyncState
from pyromax.models.enum import DeviceType
from pyromax.protocol.envelope.envelope import Envelope


class ModelAndEnvelopeTest(unittest.IsolatedAsyncioTestCase):
    def test_context_controller_binding(self) -> None:
        message = Message(message_id=1, chat_id=2, time=3, type=None, text="x", cid=None)
        self.assertIsNone(message.bot)
        with self.assertRaisesRegex(RuntimeError, "has not been bound"):
            _ = message.max_api
        api = object()
        self.assertIs(message.as_(api), message)  # type: ignore[arg-type]
        self.assertIs(message.bot, api)

    def test_session_serialization_and_string_sync_compatibility(self) -> None:
        info = SessionInfo(
            session_id="id", token="token", device_id="dev", phone="7999",
            sync='{"chats_sync": 8, "contacts_sync": 9}',  # type: ignore[arg-type]
        )
        restored = SessionInfo.from_string(info.to_string())
        self.assertEqual(restored, info)
        self.assertEqual(restored.sync.chats_sync, 8)

    def test_sync_overrides_preserve_unspecified_values(self) -> None:
        saved = SyncState(chats_sync=1, contacts_sync=2, drafts_sync=3,
                          presence_sync=4, chats_count=5, config_hash="hash")
        resolved = SyncOverrides(chats_sync=10, chats_count=0).resolve(saved)
        self.assertEqual(resolved.chats_sync, 10)
        self.assertEqual(resolved.contacts_sync, 2)
        self.assertEqual(resolved.chats_count, 0)
        self.assertEqual(resolved.config_hash, "hash")

    def test_envelope_identity_hash_and_response_matching(self) -> None:
        request = Envelope(seq=1, cmd=10, opcode=2, payload={"request": True})
        same_identity = Envelope(seq=1, cmd=10, opcode=2, payload={"different": True})
        response = Envelope(seq=1, cmd=11, opcode=2, payload={})
        self.assertEqual(request, same_identity)
        self.assertEqual(hash(request), hash(same_identity))
        self.assertTrue(request.is_my_response(response))
        self.assertFalse(request.is_my_response(Envelope(seq=2, cmd=11, opcode=2, payload={})))
        with self.assertRaises(TypeError):
            request.is_my_response(object())  # type: ignore[arg-type]

    def test_extra_config_selects_transport_from_mapper_device(self) -> None:
        web = ExtraConfig(mapper={"device_type": DeviceType.Web})
        android = ExtraConfig(mapper={"device_type": DeviceType.Android})
        self.assertIsInstance(web.transport, WebSocketTransportConfig)
        self.assertIsInstance(android.transport, SocketTransportConfig)
