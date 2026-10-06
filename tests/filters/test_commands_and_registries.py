import re
import unittest

from pyromax.encoding.registry import ENCODINGS, register_encoding
from pyromax.filters.Command import Command, CommandException, CommandObject
from pyromax.mapping.registry import MAPPERS, register_mapper
from pyromax.protocol.registry import PROTOCOLS, register_protocol
from pyromax.transport.registry import TRANSPORTS, register_transport


class CommandTest(unittest.IsolatedAsyncioTestCase):
    def test_command_object_text_and_mentioned(self) -> None:
        command = CommandObject(prefix="!", command="go", mention="bot", args="now")
        self.assertTrue(command.mentioned)
        self.assertEqual(command.text, "!go@bot now")

    def test_extract_command(self) -> None:
        self.assertEqual(
            Command.extract_command("/start@helper one two"),
            CommandObject(prefix="/", command="start", mention="helper", args="one two"),
        )

    async def test_parse_command_supports_casefold_and_regex(self) -> None:
        casefold = Command("START", ignore_case=True)
        parsed = await casefold.parse_command("/start arg", object())  # type: ignore[arg-type]
        self.assertEqual(parsed.args, "arg")

        regex = Command(re.compile(r"item-(\d+)$"))
        parsed = await regex.parse_command("/item-42", object())  # type: ignore[arg-type]
        self.assertEqual(parsed.regexp_match.group(1), "42")  # type: ignore[union-attr]

    def test_command_validation_errors(self) -> None:
        with self.assertRaises(ValueError):
            Command()
        with self.assertRaises(ValueError):
            Command(123)
        command = Command("ok", prefix="/!")
        with self.assertRaises(CommandException):
            command.validate_prefix(CommandObject(prefix="#", command="ok"))
        with self.assertRaises(CommandException):
            command.validate_command(CommandObject(command="other"))


class RegistryTest(unittest.TestCase):
    def test_registration_decorators_return_and_store_classes(self) -> None:
        cases = [
            (register_encoding, ENCODINGS),
            (register_mapper, MAPPERS),
            (register_protocol, PROTOCOLS),
            (register_transport, TRANSPORTS),
        ]
        for index, (decorator, registry) in enumerate(cases):
            name = f"test-{index}"

            class Backend:
                pass

            self.assertIs(decorator(name)(Backend), Backend)  # type: ignore[arg-type]
            self.assertIs(registry[name], Backend)
            registry.pop(name)
