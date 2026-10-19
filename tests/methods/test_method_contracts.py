import unittest

from pyromax.methods.AddReaction import AddReactionMethod
from pyromax.methods.ChangePassword import ChangePasswordMethod
from pyromax.methods.CreateFolder import CreateFolderMethod
from pyromax.methods.DeleteMessages import DeleteMessagesMethod
from pyromax.methods.ReadMessage import ReadMessageMethod
from pyromax.methods.SendMessage import SendMessageMethod
from pyromax.methods.SetPresence import SetPresenceMethod
from pyromax.methods.AddCommentReaction import AddCommentReactionMethod
from pyromax.methods.DeleteComment import DeleteCommentMethod
from pyromax.methods.EditComment import EditCommentMethod
from pyromax.methods.FetchComments import FetchCommentsMethod
from pyromax.methods.SendComment import SendCommentMethod
from pyromax.methods.SetChannelComments import SetChannelCommentsMethod

from tests.helpers.fakes import FakeApi


class MethodContractTest(unittest.IsolatedAsyncioTestCase):
    async def test_unbound_methods_fail_before_mapper_access(self) -> None:
        cases = [
            (AddReactionMethod(), (1, 2, "like"), {}),
            (DeleteMessagesMethod(), (1, [2]), {}),
            (SetPresenceMethod(), (True,), {}),
            (SendMessageMethod(), (), {"chat_id": 1, "text": "hello"}),
        ]
        for method, args, kwargs in cases:
            with self.subTest(method=type(method).__name__):
                with self.assertRaisesRegex(RuntimeError, "not bound"):
                    await method(*args, **kwargs)

    async def test_call_method_delegates_exact_public_arguments(self) -> None:
        cases = [
            (
                AddReactionMethod,
                (10, "m1", "heart"),
                {},
                {
                    "chat_id": 10,
                    "message_id": "m1",
                    "reaction_id": "heart",
                    "reaction_type": "EMOJI",
                },
            ),
            (
                DeleteMessagesMethod,
                (10, [1, 2]),
                {"for_me": True},
                {"chat_id": 10, "message_ids": [1, 2], "for_me": True},
            ),
            (SetPresenceMethod, (False,), {}, {"online": False}),
            (
                ReadMessageMethod,
                (10, 20, 30),
                {},
                {"chat_id": 10, "message_id": 20, "mark": 30, "typeof": "READ_MESSAGE"},
            ),
            (
                CreateFolderMethod,
                ("work", [1, 2]),
                {},
                {
                    "title": "work",
                    "chat_include": [1, 2],
                    "filters": None,
                    "folder_id": None,
                },
            ),
            (
                ChangePasswordMethod,
                ("old", "new"),
                {"hint": "h"},
                {
                    "password_old": "old",
                    "password_new": "new",
                    "hint": "h",
                    "expected_capabilities": None,
                },
            ),
            (
                SendCommentMethod,
                (10, 20),
                {"text": "comment", "reply_to": 30, "notify": False},
                {
                    "chat_id": 10,
                    "post_id": 20,
                    "text": "comment",
                    "reply_to": 30,
                    "attachments": None,
                    "notify": False,
                },
            ),
            (
                FetchCommentsMethod,
                (10, 20),
                {},
                {
                    "chat_id": 10,
                    "post_id": 20,
                    "from_": None,
                    "backward": 30,
                    "get_messages": True,
                    "forward": 0,
                },
            ),
            (
                EditCommentMethod,
                (10, 20, 30),
                {"text": "edited"},
                {
                    "chat_id": 10,
                    "post_id": 20,
                    "message_id": 30,
                    "text": "edited",
                    "attachments": None,
                },
            ),
            (
                DeleteCommentMethod,
                (10, 20, [30]),
                {},
                {
                    "chat_id": 10,
                    "post_id": 20,
                    "message_ids": [30],
                    "for_me": False,
                },
            ),
            (
                AddCommentReactionMethod,
                (10, 20, 30, "heart"),
                {},
                {
                    "chat_id": 10,
                    "post_id": 20,
                    "message_id": 30,
                    "reaction": "heart",
                },
            ),
            (
                SetChannelCommentsMethod,
                (10, True),
                {},
                {"chat_id": 10, "enabled": True},
            ),
        ]
        marker = object()
        for method_type, args, kwargs, expected in cases:
            with self.subTest(method=method_type.__name__):
                api = FakeApi(marker)
                method = method_type().as_(api)  # type: ignore[arg-type]
                self.assertIs(await method(*args, **kwargs), marker)
                self.assertEqual(api.mapper.calls[0].method, method_type)
                self.assertEqual(api.mapper.calls[0].kwargs, expected)

    async def test_send_message_normalizes_missing_attachments(self) -> None:
        marker = object()
        api = FakeApi(marker)
        method = SendMessageMethod().as_(api)  # type: ignore[arg-type]

        self.assertIs(await method(chat_id=4, text="hello", custom=True), marker)
        self.assertEqual(
            api.mapper.direct_calls,
            [
                (
                    "send_message",
                    {
                        "chat_id": 4,
                        "text": "hello",
                        "attaches": [],
                        "notify": True,
                        "send_at": None,
                        "custom": True,
                    },
                )
            ],
        )

    async def test_send_message_forwards_send_at(self) -> None:
        marker = object()
        api = FakeApi(marker)
        method = SendMessageMethod().as_(api)  # type: ignore[arg-type]

        self.assertIs(
            await method(chat_id=4, text="later", send_at=1_800_000_000),
            marker,
        )
        self.assertEqual(
            api.mapper.direct_calls[0][1]["send_at"],
            1_800_000_000,
        )
