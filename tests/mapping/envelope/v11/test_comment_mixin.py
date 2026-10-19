import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from pyromax.mapping.envelope.v11.mixins.chat import ChatMixin
from pyromax.mapping.envelope.v11.mixins.message import MessageMixin
from pyromax.models import Chat, CommentsInfoUpdate, EmojiReaction, Message


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

    async def test_get_comments_maps_and_binds_messages(self) -> None:
        class Target:
            send = AsyncMock(
                return_value=SimpleNamespace(
                    payload={"messages": [{"id": 30, "text": "comment"}]}
                )
            )
            bind_api_instance = Mock(side_effect=lambda model: model)

        comments = await MessageMixin.get_comments(
            Target(),
            chat_id=10,
            post_id=20,
            message_ids=[30],
        )

        self.assertEqual(len(comments), 1)
        self.assertIsInstance(comments[0], Message)
        self.assertEqual(comments[0].message_id, 30)
        self.assertEqual(comments[0].chat_id, 10)
        self.assertTrue(Target.send.await_args.kwargs["check_errors"])

    async def test_remove_comment_reaction_maps_remove_status(self) -> None:
        class Target:
            send = AsyncMock(
                return_value=SimpleNamespace(
                    payload={
                        "reactionInfo": {
                            "yourReaction": None,
                            "totalCount": 0,
                            "counters": [],
                        }
                    }
                )
            )
            bind_api_instance = Mock(side_effect=lambda model: model)

        reaction = await MessageMixin.remove_comment_reaction(
            Target(),
            chat_id=10,
            post_id=20,
            message_id=30,
        )

        self.assertIsInstance(reaction, EmojiReaction)
        self.assertEqual(reaction.status, "REMOVE")
        self.assertTrue(Target.send.await_args.kwargs["check_errors"])

    async def test_get_comments_info_maps_counters(self) -> None:
        class Target:
            send = AsyncMock(
                return_value=SimpleNamespace(
                    payload={
                        "commentsInfoUpdates": [
                            {
                                "postId": 20,
                                "commentsInfo": {"totalCount": 7},
                            },
                            {"postId": 21, "commentsInfo": None},
                        ]
                    }
                )
            )
            bind_api_instance = Mock(side_effect=lambda model: model)

        updates = await MessageMixin.get_comments_info(
            Target(),
            chat_id=10,
            post_ids=[20, 21],
        )

        self.assertEqual(len(updates), 2)
        self.assertIsInstance(updates[0], CommentsInfoUpdate)
        self.assertEqual(updates[0].comments_info.total_count, 7)
        self.assertIsNone(updates[1].comments_info)

    async def test_comment_mutations_check_api_errors(self) -> None:
        class Target:
            send = AsyncMock(return_value=SimpleNamespace(payload={}))

        target = Target()
        await MessageMixin.subscribe_comments(target, 10, 20, subscribe=False)
        deleted = await MessageMixin.delete_user_comments(target, 10, 20, 40, 30)

        self.assertTrue(deleted)
        self.assertEqual(Target.send.await_count, 2)
        for call in Target.send.await_args_list:
            self.assertTrue(call.kwargs["check_errors"])

    async def test_set_channel_comments_checks_api_errors(self) -> None:
        class Target:
            send = AsyncMock(return_value=SimpleNamespace(payload={}))

        await ChatMixin.set_channel_comments(Target(), chat_id=10, enabled=True)

        self.assertTrue(Target.send.await_args.kwargs["check_errors"])

    async def test_block_comment_author_checks_errors_and_reports_success(self) -> None:
        class Target:
            send = AsyncMock(return_value=SimpleNamespace(payload={}))

        blocked = await ChatMixin.block_comment_author(
            Target(),
            chat_id=10,
            post_id=20,
            user_ids=[40],
            message_id=30,
            clean_msg_period=-1,
        )

        self.assertTrue(blocked)
        self.assertTrue(Target.send.await_args.kwargs["check_errors"])
