import unittest

from pyromax.models.Chat import Chat
from pyromax.models.Message import Message

from tests.helpers.fakes import FakeApi


def make_message(message_id: int | str = 7) -> Message:
    return Message(
        message_id=message_id,
        chat_id=10,
        time=123,
        type="USER",
        text="hello",
        cid=None,
    )


class BoundMessageTest(unittest.IsolatedAsyncioTestCase):
    async def test_message_actions_delegate_identifiers_and_options(self) -> None:
        marker = object()
        api = FakeApi(marker)
        message = make_message().as_(api)  # type: ignore[arg-type]

        await message.forward(20, notify=False)
        await message.pin(notify_pin=False)
        await message.edit("changed", attachments=[])
        await message.delete(for_me=True)
        await message.read()
        await message.react("heart")
        await message.unreact()
        await message.get_reactions()

        self.assertEqual(api.calls, [
            ("forward_message", {"from_chat_id": 10, "to_chat_id": 20, "message_id": 7, "notify": False}),
            ("pin_message", {"chat_id": 10, "message_id": 7, "notify": False}),
            ("edit_message", {"chat_id": 10, "message_id": 7, "text": "changed", "attachments": []}),
            ("delete_messages", {"chat_id": 10, "message_ids": [7], "for_me": True}),
            ("read_message", {"chat_id": 10, "message_id": 7}),
            ("add_reaction", {"chat_id": 10, "message_id": 7, "reaction_id": "heart"}),
            ("remove_reaction", {"chat_id": 10, "message_id": 7}),
            ("get_reactions", {"chat_id": 10, "message_ids": [7]}),
        ])

    async def test_reply_constructs_reply_link(self) -> None:
        marker = object()
        api = FakeApi(marker)
        message = make_message("server-id").as_(api)  # type: ignore[arg-type]

        self.assertIs(await message.reply("answer"), marker)
        method_name, kwargs = api.calls[0]
        self.assertEqual(method_name, "__call__")
        self.assertEqual(kwargs["class_of_method"].__name__, "SendMessageMethod")
        self.assertEqual(kwargs["chat_id"], 10)
        self.assertEqual(kwargs["link"].type, "REPLY")
        self.assertEqual(kwargs["link"].message_id, "server-id")


class BoundChatTest(unittest.IsolatedAsyncioTestCase):
    async def test_answer_uses_chat_id_and_normalizes_empty_text(self) -> None:
        marker = object()
        api = FakeApi(marker)
        chat = Chat(id=5, type="CHAT", status="ACTIVE", owner=1).as_(api)  # type: ignore[arg-type]

        self.assertIs(await chat.answer(None, notify=False), marker)
        self.assertEqual(api.calls, [
            ("send_message", {
                "chat_id": 5, "text": "", "link": None, "attaches": None, "notify": False
            })
        ])
