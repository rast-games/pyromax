import unittest

from pyromax.core import MaxApi
from pyromax.mapping.envelope.v11.constants import Opcode
from pyromax.mapping.envelope.v11.methods.immutable.chats import (
    SetChannelCommentsMethod,
)
from pyromax.mapping.envelope.v11.methods.immutable.messages import (
    AddCommentReactionMethod,
    DeleteCommentMethod,
    EditCommentMethod,
    FetchCommentsMethod,
    SendCommentMethod,
)
from pyromax.models import MessageLink
from pyromax.protocol.envelope import Envelope


class CommentPayloadTest(unittest.IsolatedAsyncioTestCase):
    def test_client_exposes_comment_api(self) -> None:
        for name in (
            "send_comment",
            "fetch_comments",
            "edit_comment",
            "delete_comment",
            "add_comment_reaction",
            "set_channel_comments",
        ):
            with self.subTest(name=name):
                self.assertTrue(hasattr(MaxApi, name))

    async def test_send_comment_payload_contains_post_id_and_reply(self) -> None:
        result = await SendCommentMethod(
            chat_id=10,
            post_id=20,
            text="hello",
            cid=-1,
            attaches=[],
            elements=[],
            link=MessageLink(type="REPLY", message_id=30),
            notify=False,
        )(Envelope(seq=1, payload={}))

        self.assertEqual(result.opcode, Opcode.SEND_MESSAGE)
        self.assertEqual(result.payload["postId"], 20)
        self.assertEqual(result.payload["chatId"], 10)
        self.assertEqual(
            result.payload["message"]["link"],
            {"type": "REPLY", "messageId": 30},
        )
        self.assertFalse(result.payload["notify"])

    async def test_fetch_comments_payload_matches_history_contract(self) -> None:
        result = await FetchCommentsMethod(
            chat_id=10,
            post_id=20,
            forward=0,
            backward=30,
            backward_time=0,
            forward_time=0,
            from_time=-1,
            item_type="REGULAR",
            get_chat=False,
            get_messages=True,
            interactive=False,
        )(Envelope(seq=1, payload={}))

        self.assertEqual(result.opcode, Opcode.GET_CHAT_MESSAGES_PER_CHUNK)
        self.assertEqual(result.payload["postId"], 20)
        self.assertEqual(result.payload["from"], -1)
        self.assertEqual(result.payload["backward"], 30)

    async def test_edit_delete_and_reaction_payloads_contain_post_id(self) -> None:
        cases = [
            (
                EditCommentMethod(
                    chat_id=10,
                    post_id=20,
                    message_id=30,
                    text="edited",
                    elements=[],
                    attaches=[],
                ),
                Opcode.EDIT_MESSAGE,
            ),
            (
                DeleteCommentMethod(
                    chat_id=10,
                    post_id=20,
                    message_ids=[30],
                    for_me=False,
                ),
                Opcode.DELETE_MESSAGE,
            ),
            (
                AddCommentReactionMethod(
                    chat_id=10,
                    post_id=20,
                    message_id=30,
                    reaction_id="heart",
                    reaction_type="EMOJI",
                ),
                Opcode.ADD_REACTION,
            ),
        ]

        for method, opcode in cases:
            with self.subTest(method=type(method).__name__):
                result = await method(Envelope(seq=1, payload={}))
                self.assertEqual(result.opcode, opcode)
                self.assertEqual(result.payload["postId"], 20)

    async def test_set_channel_comments_uses_comments_option(self) -> None:
        result = await SetChannelCommentsMethod(chat_id=10, enabled=False)(
            Envelope(seq=1, payload={})
        )

        self.assertEqual(result.opcode, Opcode.CHAT_UPDATE)
        self.assertEqual(
            result.payload,
            {"chatId": 10, "options": {"COMMENTS": False}},
        )
