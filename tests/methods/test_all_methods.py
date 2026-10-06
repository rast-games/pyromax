import inspect
import unittest
from pathlib import Path
from typing import Any

import pyromax.methods as methods
from pyromax.methods import BaseMaxApiMethod

from tests.helpers.fakes import FakeApi


def required_arguments(method_type: type[BaseMaxApiMethod[Any]]) -> dict[str, Any]:
    """Build harmless values for required public method arguments."""
    values: dict[str, Any] = {
        "answer_ids": [],
        "chat_id": 1,
        "chat_ids": [1],
        "chat_include": [],
        "clean_msg_period": 0,
        "contact_id": 1,
        "contacts": [],
        "data": b"",
        "file": object(),
        "first_name": "name",
        "first_user_id": 1,
        "folder_id": "folder",
        "folder_ids": ["folder"],
        "from_chat_id": 1,
        "link": "link",
        "mark": 1,
        "member_ids": [],
        "message_id": 1,
        "message_ids": [1],
        "name": "name",
        "online": True,
        "participant_ids": [],
        "password": "password",
        "password_new": "new",
        "password_old": "old",
        "permissions": [],
        "phone": "+79990000000",
        "poll": object(),
        "poll_id": 1,
        "privacy_settings": object(),
        "qr_link": "qr",
        "reaction_id": "heart",
        "second_user_id": 2,
        "title": "title",
        "to_chat_id": 2,
        "typeof": object,
        "user_id": 1,
        "user_ids": [],
    }
    signature = inspect.signature(method_type.__call__)
    return {
        parameter.name: values[parameter.name]
        for parameter in signature.parameters.values()
        if parameter.name != "self"
        and parameter.default is inspect.Parameter.empty
        and parameter.kind
        not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    }


class AllMethodsTest(unittest.IsolatedAsyncioTestCase):
    def concrete_method_types(self) -> list[type[BaseMaxApiMethod[Any]]]:
        return sorted(
            {
                exported
                for name in methods.__all__
                if name != "BaseMaxApiMethod"
                and inspect.isclass(exported := getattr(methods, name))
                and issubclass(exported, BaseMaxApiMethod)
            },
            key=lambda item: item.__name__,
        )

    def test_public_exports_contain_every_concrete_method(self) -> None:
        exported = set(self.concrete_method_types())
        discovered: set[type[BaseMaxApiMethod[Any]]] = set()
        package_path = inspect.getfile(methods)
        package_dir = Path(package_path).parent

        for source in package_dir.glob("*.py"):
            if source.stem in {"Base", "__init__"}:
                continue
            module = __import__(f"pyromax.methods.{source.stem}", fromlist=["*"])
            discovered.update(
                value
                for value in vars(module).values()
                if inspect.isclass(value)
                and value is not BaseMaxApiMethod
                and issubclass(value, BaseMaxApiMethod)
                and value.__module__ == module.__name__
            )

        self.assertEqual(exported, discovered)
        self.assertGreaterEqual(len(exported), 50)

    async def test_every_public_method_rejects_an_unbound_call(self) -> None:
        for method_type in self.concrete_method_types():
            with self.subTest(method=method_type.__name__):
                method = method_type()
                with self.assertRaisesRegex(RuntimeError, "not bound"):
                    await method(**required_arguments(method_type))

    async def test_every_public_method_delegates_when_bound(self) -> None:
        for method_type in self.concrete_method_types():
            with self.subTest(method=method_type.__name__):
                api = FakeApi([])
                method = method_type().as_(api)  # type: ignore[arg-type]

                result = await method(**required_arguments(method_type))

                self.assertEqual(result, [])
                self.assertEqual(
                    len(api.mapper.calls) + len(api.mapper.direct_calls),
                    1,
                    f"{method_type.__name__} must delegate exactly once",
                )
