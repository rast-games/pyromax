import unittest
from datetime import datetime, timedelta, timezone

from pyromax.mapping.envelope.v11.methods.immutable.messages import (
    SendMessageMethod,
    _convert_send_at,
)
from pyromax.mapping.envelope.v11.payloads.models import MessageMappingModel
from pyromax.mapping.envelope.v11.translate.ToDTO import translate_models
from pyromax.models import Message
from pyromax.protocol.envelope import Envelope


class SendAtTest(unittest.IsolatedAsyncioTestCase):
    def test_convert_send_at_supported_values_to_milliseconds(self) -> None:
        absolute = datetime(2027, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        self.assertEqual(
            _convert_send_at(absolute),
            int(absolute.timestamp() * 1000),
        )
        self.assertEqual(_convert_send_at(1_800_000_000), 1_800_000_000_000)

        delay = timedelta(seconds=30)
        lower_bound = int((datetime.now() + delay).timestamp() * 1000)
        converted = _convert_send_at(delay)
        upper_bound = int((datetime.now() + delay).timestamp() * 1000)
        self.assertLessEqual(lower_bound, converted)
        self.assertLessEqual(converted, upper_bound)

    async def test_send_message_serializes_delayed_attributes(self) -> None:
        absolute = datetime(2027, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        request = Envelope(seq=1, payload={})

        result = await SendMessageMethod(
            chat_id=10,
            text="later",
            cid=-123,
            attaches=[],
            elements=[],
            notify=False,
            send_at=absolute,
        )(request)

        self.assertEqual(
            result.payload["message"]["delayedAttributes"],
            {
                "timeToFire": int(absolute.timestamp() * 1000),
                "notifySender": False,
            },
        )
        self.assertFalse(result.payload["notify"])

    async def test_zero_send_at_sends_immediately(self) -> None:
        request = Envelope(seq=1, payload={})

        result = await SendMessageMethod(
            chat_id=10,
            text="now",
            cid=-123,
            attaches=[],
            elements=[],
            send_at=0,
        )(request)

        self.assertNotIn("delayedAttributes", result.payload["message"])

    def test_delayed_attributes_are_preserved_on_domain_message(self) -> None:
        mapped = MessageMappingModel.model_validate(
            {
                "id": 123,
                "chatId": 10,
                "time": 1_800_000_000_000,
                "text": "later",
                "delayedAttributes": {
                    "timeToFire": 1_800_000_000_000,
                    "notifySender": False,
                    "notifyOpponents": True,
                },
            }
        )

        message = translate_models(mapped)

        self.assertIsInstance(message, Message)
        assert isinstance(message, Message)
        self.assertIsNotNone(message.delayed_attributes)
        assert message.delayed_attributes is not None
        self.assertEqual(
            message.delayed_attributes.time_to_fire,
            1_800_000_000_000,
        )
        self.assertFalse(message.delayed_attributes.notify_sender)
        self.assertTrue(message.delayed_attributes.notify_opponents)
