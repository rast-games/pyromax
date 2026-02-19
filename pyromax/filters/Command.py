from collections.abc import Iterable, Sequence
import re
from dataclasses import dataclass, field, replace
from re import Match, Pattern
from typing import TYPE_CHECKING, Any, cast

from .base import Filter
from pyromax.types import Message

if TYPE_CHECKING:
    from pyromax.api import MaxApi

CommandPatternType = str | Pattern[str]

class CommandException(Exception):
    pass

@dataclass(frozen=True)
class CommandObject:
    """
    Instance of this object is always has command and it prefix.
    Can be passed as keyword argument **command** to the handler
    """

    prefix: str = "/"
    """Command prefix"""
    command: str = ""
    """Command without prefix and mention"""
    mention: str | None = None
    """Mention (if available)"""
    args: str | None = field(repr=False, default=None)
    """Command argument"""
    regexp_match: Match[str] | None = field(repr=False, default=None)
    """Will be presented match result if the command is presented as regexp in filter"""
    magic_result: Any | None = field(repr=False, default=None)

    @property
    def mentioned(self) -> bool:
        """
        This command has mention?
        """
        return bool(self.mention)

    @property
    def text(self) -> str:
        """
        Generate original text from object
        """
        line = self.prefix + self.command
        if self.mention:
            line += "@" + self.mention
        if self.args:
            line += " " + self.args
        return line


class Command(Filter):
    """
    This filter can be helpful for handling commands from the text messages.

    Works only with :class:`aiogram.types.message.Message` events which have the :code:`text`.
    """

    __slots__ = (
        "commands",
        "ignore_case",
        "ignore_mention",
        "magic",
        "prefix",
    )

    def __init__(
        self,
        *values,
        commands: None = None,
        prefix: str = "/",
        ignore_case: bool = False,
        ignore_mention: bool = False,
        magic: None = None,
    ):
        """
        List of commands (string or compiled regexp patterns)

        :param prefix: Prefix for command.
            Prefix is always a single char but here you can pass all of allowed prefixes,
            for example: :code:`"/!"` will work with commands prefixed
            by :code:`"/"` or :code:`"!"`.
        :param ignore_case: Ignore case (Does not work with regexp, use flags instead)
        :param ignore_mention: Ignore bot mention. By default,
            bot can not handle commands intended for other bots
        :param magic: Validate command object via Magic filter after all checks done
        """
        if commands is None:
            commands = []
        if isinstance(commands, (str, Pattern)):
            commands = [commands]

        if not isinstance(commands, Iterable):
            msg = (
                "Command filter only supports str, re.Pattern, BotCommand object or their Iterable"
            )
            raise ValueError(msg)

        items = []
        for command in (*values, *commands):
            # if isinstance(command, BotCommand):
            #     command = command.command
            if not isinstance(command, (str, Pattern)):
                msg = (
                    "Command filter only supports str, re.Pattern, BotCommand object"
                    " or their Iterable"
                )
                raise ValueError(msg)
            if ignore_case and isinstance(command, str):
                command = command.casefold()
            items.append(command)

        if not items:
            msg = "At least one command should be specified"
            raise ValueError(msg)

        self.commands = tuple(items)
        self.prefix = prefix
        self.ignore_case = ignore_case
        self.ignore_mention = ignore_mention
        self.magic = magic

    async def __call__(self, message: Message, max_api: 'MaxApi') -> bool | CommandObject:
        if not isinstance(message, Message):
            return False
        text = message.text
        if not text:
            return False

        try:
            command = await self.parse_command(text=text, max_api=max_api)
        except CommandException as e:
            return False

        # result = {type(command): command}
        return command


    @classmethod
    def extract_command(cls, text: str) -> CommandObject:
        # First step: separate command with arguments
        # "/command@mention arg1 arg2" -> "/command@mention", ["arg1 arg2"]
        try:
            full_command, *args = text.split(maxsplit=1)
        except ValueError as e:
            msg = "not enough values to unpack"
            raise CommandException(msg) from e

        # Separate command into valuable parts
        # "/command@mention" -> "/", ("command", "@", "mention")
        prefix, (command, _, mention) = full_command[0], full_command[1:].partition("@")
        return CommandObject(
            prefix=prefix,
            command=command,
            mention=mention or None,
            args=args[0] if args else None,
        )

    def validate_prefix(self, command: CommandObject) -> None:
        if command.prefix not in self.prefix:
            msg = "Invalid command prefix"
            raise CommandException(msg)

    # async def validate_mention(self, max_api: 'MaxApi', command: CommandObject) -> None:
    #     if command.mention and not self.ignore_mention:
    #         me = await max_api.me()
    #         if me.username and command.mention.lower() != me.username.lower():
    #             msg = "Mention did not match"
    #             raise CommandException(msg)

    def validate_command(self, command: CommandObject) -> CommandObject:
        for allowed_command in cast(Sequence[CommandPatternType], self.commands):
            # Command can be presented as regexp pattern or raw string
            # then need to validate that in different ways
            if isinstance(allowed_command, Pattern):  # Regexp
                result = allowed_command.match(command.command)
                if result:
                    return replace(command, regexp_match=result)

            command_name = command.command
            if self.ignore_case:
                command_name = command_name.casefold()

            if command_name == allowed_command:  # String
                return command
        msg = "Command did not match pattern"
        raise CommandException(msg)

    async def parse_command(self, text: str, max_api: 'MaxApi') -> CommandObject:
        """
        Extract command from the text and validate

        :param text:
        :param max_api:
        :return:
        """
        command = self.extract_command(text)
        self.validate_prefix(command=command)
        # await self.validate_mention(bot=max_api, command=command)
        command = self.validate_command(command)
        # command = self.do_magic(command=command)
        return command


class CommandStart(Command):
    def __init__(
            self,
            ignore_case: bool = False,
            ignore_mention: bool = False,
    ):
        super().__init__(
            "start",
            prefix="/",
            ignore_case=ignore_case,
            ignore_mention=ignore_mention,
        )

    def __str__(self) -> str:
        return self._signature_to_string(
            ignore_case=self.ignore_case,
            ignore_mention=self.ignore_mention,
        )