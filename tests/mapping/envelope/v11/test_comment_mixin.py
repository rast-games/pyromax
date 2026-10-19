import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from pyromax.mapping.envelope.v11.mixins.chat import ChatMixin
from pyromax.mapping.envelope.v11.mixins.message import MessageMixin
from pyromax.models import Chat


class CommentMixinTest(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_comments_returns_ids_when_messages_are_disabled(self) -> None:
        class Target:
            send = AsyncMock(
                return_value=SimpleNamespace(payload={"messageIds": [30, "31"]})
            )

        comments = await MessageMixin.fetch_comments(
            Target(),
            chat_id=10,
            post_id=20,
            get_messages=False,
        )

        self.assertEqual(comments, [30, "31"])

    async def test_fetch_comment_ids_can_include_chat(self) -> None:
        class Target:
            send = AsyncMock(
                return_value=SimpleNamespace(
                    payload={
                        "messageIds": [30, "31"],
                        "chat": {
                            "id": 10,
                            "type": "CHANNEL",
                            "status": "ACTIVE",
                            "owner": 1,
                        },
                    }
                )
            )
            bind_api_instance = Mock(side_effect=lambda model: model)

        comments, chat = await MessageMixin.fetch_comments(
            Target(),
            chat_id=10,
            post_id=20,
            get_messages=False,
            get_chat=True,
        )

        self.assertEqual(comments, [30, "31"])
        self.assertIsInstance(chat, Chat)
        self.assertEqual(chat.id, 10)
        method = Target.send.await_args.kwargs["method"]
        self.assertTrue(method.args["get_chat"])

    async def test_fetch_comment_messages_can_include_chat(self) -> None:
        class Target:
            send = AsyncMock(
                return_value=SimpleNamespace(
                    payload={
                        "messages": [],
                        "chat": {
                            "id": 10,
                            "type": "CHANNEL",
                            "status": "ACTIVE",
                            "owner": 1,
                        },
                    }
                )
            )
            bind_api_instance = Mock(side_effect=lambda model: model)

        comments, chat = await MessageMixin.fetch_comments(
            Target(),
            chat_id=10,
            post_id=20,
            get_chat=True,
        )

        self.assertEqual(comments, [])
        self.assertIsInstance(chat, Chat)
        self.assertEqual(chat.id, 10)

    async def test_delete_comment_checks_api_errors(self) -> None:
        class Target:
            send = AsyncMock(return_value=SimpleNamespace(payload={}))

        deleted = await MessageMixin.delete_comment(
            Target(),
            chat_id=10,
            post_id=20,
            message_ids=[30],
        )

        self.assertTrue(deleted)
        self.assertTrue(Target.send.await_args.kwargs["check_errors"])

    async def test_set_channel_comments_checks_api_errors(self) -> None:
        class Target:
            send = AsyncMock(return_value=SimpleNamespace(payload={}))

        await ChatMixin.set_channel_comments(Target(), chat_id=10, enabled=True)

        self.assertTrue(Target.send.await_args.kwargs["check_errors"])
