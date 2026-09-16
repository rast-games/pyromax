from collections.abc import Iterable
from typing import cast, Any, overload, Literal

from ...methods import (
    SendMessageMethod,
    ForwardMessageMethod,
    GetMessagesMethod,
    EditMessageMethod,
    GetChatHistoryMethod,
    DeleteMessagesMethod,
    PinMessageMethod,
    AddReactionMethod,
    RemoveReactionMethod,
    GetReactionsMethod,
    ReadMessageMethod,
    CreatePollMethod,
    VotePollMethod,
)

from ...exceptions import SendMessageError, MapperApiError, ReactionError

from ...models import (
    BaseFileAttachment,
    MessageLink,
    Message,
    EmojiReaction,
    ReadState,
    Poll,
    PollState,
    Chat,
)
from .CoreMixinsProtocol import CoreMixinsProtocol


class MessageMixin(CoreMixinsProtocol):
    async def send_message(
        self,
        chat_id: int,
        text: str = "",
        attaches: list[BaseFileAttachment] | None = None,
        link: MessageLink | None = None,
        notify: bool = True,
    ) -> Message | None:
        """Send a message to a chat.

        :param chat_id: Target chat identifier.
        :type chat_id: int
        :param text: Message text.
        :type text: str
        :param attaches: Optional list of attachments.
        :type attaches: list[BaseFileAttachment] | None
        :param link: Optional message link object.
        :type link: MessageLink | None

        :returns: API response returned by the mapper.
        :rtype: Message | None

        :raises SendMessageError: If message sending fails.

        :param notify: Whether MAX should notify affected users.
        :type notify: bool
        :raises AttributeError: If logger not initialized in MaxApi instance.
        """

        try:
            return cast(
                Message | None,
                await self(
                    SendMessageMethod,
                    text=text,
                    chat_id=chat_id,
                    attaches=attaches,
                    link=link,
                    notify=notify,
                ),
            )
        except SendMessageError as e:
            if self._logger is None:
                raise AttributeError("logger not initialized in MaxApi instance")
            self._logger.warning("Failed to send message: %s", e)
            raise e

    async def forward_message(
        self,
        message_id: int | str,
        to_chat_id: int,
        from_chat_id: int,
        notify: bool = True,
    ) -> Message | None:
        """Forward message.

        :param message_id: Identifier of the message.
        :type message_id: int | str
        :param to_chat_id: Identifier of the destination chat.
        :type to_chat_id: int
        :param from_chat_id: Identifier of the source chat.
        :type from_chat_id: int
        :param notify: Whether MAX should notify affected users.
        :type notify: bool
        :returns: The resulting Message | None value.
        :rtype: Message | None
        :raises AttributeError: If logger not initialized in MaxApi instance.
        """
        try:
            return cast(
                Message | None,
                await self(
                    ForwardMessageMethod,
                    message_id=message_id,
                    to_chat_id=to_chat_id,
                    from_chat_id=from_chat_id,
                    notify=notify,
                ),
            )
        except SendMessageError as e:
            if self._logger is None:
                raise AttributeError("logger not initialized in MaxApi instance")
            self._logger.warning("Failed to forward message: %s", e)
            raise e

    async def edit_message(
        self,
        chat_id: int,
        message_id: int | str,
        text: str | None = None,
        attaches: list[BaseFileAttachment] | None = None,
        **kwargs: Any,
    ) -> Message:
        """Edit message.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_id: Identifier of the message.
        :type message_id: int | str
        :param text: Message or textual content.
        :type text: str | None
        :param attaches: Attachments associated with the message.
        :type attaches: list[BaseFileAttachment] | None
        # :param kwargs: Keyword arguments forwarded to the wrapped callable.
        # :type kwargs: Any
        :returns: The resulting Message value.
        :rtype: Message
        """

        return cast(
            Message,
            await self(
                EditMessageMethod,
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                attaches=attaches,
            ),
        )

    async def get_messages(
        self, chat_id: int, message_ids: Iterable[str] | Iterable[int]
    ) -> list[Message]:
        """Retrieve messages.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_ids: Identifiers of the messages.
        :type message_ids: Iterable[str] | Iterable[int]
        :returns: The resulting collection.
        :rtype: list[Message]
        """

        return cast(
            list[Message],
            await self(
                GetMessagesMethod,
                chat_id=chat_id,
                message_ids=message_ids,
            ),
        )

    async def get_message(self, chat_id: int, message_id: int | str) -> Message | None:
        """Retrieve message.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_id: Identifier of the message.
        :type message_id: int | str
        :returns: The resulting Message | None value.
        :rtype: Message | None
        """
        msg_ids: list[int] | list[str]
        if isinstance(message_id, str):
            msg_ids = [message_id]
        else:
            msg_ids = [message_id]

        msgs = await self.get_messages(chat_id=chat_id, message_ids=msg_ids)
        return msgs[0] if msgs else None

    @overload
    async def get_chat_history(
        self,
        chat_id: int,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = ...,
        item_type: Literal["DELAYED", "REGULAR"] = ...,
        get_chat: Literal[False] = False,
        get_messages: Literal[True] = True,
        interactive: bool = ...,
    ) -> list[Message]:
        pass

    @overload
    async def get_chat_history(
        self,
        chat_id: int,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = None,
        item_type: Literal["DELAYED", "REGULAR"] = ...,
        get_chat: Literal[True] = True,
        get_messages: Literal[True] = True,
        interactive: bool = ...,
    ) -> tuple[list[Message], Chat | None]:
        pass

    @overload
    async def get_chat_history(
        self,
        chat_id: int,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = None,
        item_type: Literal["DELAYED", "REGULAR"] = ...,
        get_chat: Literal[False] = False,
        get_messages: Literal[False] = False,
        interactive: bool = ...,
    ) -> list[str | int]:
        pass

    @overload
    async def get_chat_history(
        self,
        chat_id: int,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = None,
        item_type: Literal["DELAYED", "REGULAR"] = ...,
        get_chat: Literal[True] = True,
        get_messages: Literal[False] = False,
        interactive: bool = ...,
    ) -> tuple[list[str | int], Chat | None]:
        pass

    @overload
    async def get_chat_history(
        self,
        chat_id: int,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = ...,
        item_type: Literal["DELAYED", "REGULAR"] = ...,
        get_chat: bool = ...,
        get_messages: bool = ...,
        interactive: bool = ...,
    ) -> (
        list[Message]
        | list[str | int]
        | tuple[list[Message] | list[str | int], Chat | None]
    ): ...

    async def get_chat_history(
        self,
        chat_id: int,
        forward: int = 0,
        backward: int = 40,
        backward_time: int = 0,
        forward_time: int = 0,
        from_time: int | None = None,
        item_type: Literal["DELAYED", "REGULAR"] = "REGULAR",
        get_chat: bool = False,
        get_messages: bool = True,
        interactive: bool = False,
    ) -> (
        list[Message]
        | list[str | int]
        | tuple[list[Message] | list[str | int], Chat | None]
    ):
        """Retrieve chat history.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param forward: How many messages to load ahead from ``from_time``.
        :type forward: int
        :param backward: How many messages to load back from ``from_time``.
        :type backward: int
        :param backward_time: Look-back time window in milliseconds.
        :type backward_time: int
        :param forward_time: Forward time window in milliseconds.
        :type forward_time: int
        :param from_time: The reference point in Unix time (milliseconds). If ``None``, the current moment is used.
        :type from_time: int | None
        :param item_type: History item type.
        :type item_type: Literal['DELAYED', 'REGULAR']
        :param get_chat: Request chat data along with the history.
        :type get_chat: bool
        :param get_messages: The get messages value.
        :type get_messages: bool
        :param interactive: Request the messages themselves.
        :type interactive: bool
        :returns: History items, paired with the requested chat when ``get_chat`` is true.
        :rtype: list[Message] | list[str | int] | tuple[list[Message] | list[str | int], Chat | None]
        """

        return cast(
            list[Message]
            | list[str | int]
            | tuple[list[Message] | list[str | int], Chat | None],
            await self(
                GetChatHistoryMethod,
                chat_id=chat_id,
                forward=forward,
                backward=backward,
                backward_time=backward_time,
                forward_time=forward_time,
                from_time=from_time,
                item_type=item_type,
                get_chat=get_chat,
                get_messages=get_messages,
                interactive=interactive,
            ),
        )

    async def delete_messages(
        self,
        chat_id: int,
        message_ids: list[str] | list[int],
        for_me: bool = False,
    ) -> None:
        """Delete messages.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_ids: Identifiers of the messages.
        :type message_ids: list[str] | list[int]
        :param for_me: Delete only for the current account.
        :type for_me: bool
        """
        return cast(
            None,
            await self(
                DeleteMessagesMethod,
                chat_id=chat_id,
                message_ids=message_ids,
                for_me=for_me,
            ),
        )

    async def pin_message(
        self, chat_id: int, message_id: int | str, notify: bool = True
    ) -> None:
        """Pin message.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_id: Identifier of the message.
        :type message_id: int | str
        :param notify: Whether MAX should notify affected users.
        :type notify: bool
        """
        return cast(
            None,
            await self(
                PinMessageMethod,
                chat_id=chat_id,
                message_id=message_id,
                notify=notify,
            ),
        )

    async def add_reaction(
        self,
        chat_id: int,
        message_id: int | str,
        reaction_id: str,
        reaction_type: str = "EMOJI",
    ) -> EmojiReaction | None:
        """Add an emoji reaction to a message.

        :param chat_id: Identifier of the chat containing the message.
        :type chat_id: int
        :param message_id: int | str
        :type message_id: int | str
        :param reaction_id: str
        :type reaction_id: str
        :param reaction_type: str
        :type reaction_type: str

        :returns: info about reaction or None if cannot get this info
        :rtype: EmojiReaction | None

        :raises ReactionError: if adding reaction failed
        """

        try:
            return cast(
                EmojiReaction | None,
                await self(
                    AddReactionMethod,
                    chat_id=chat_id,
                    message_id=message_id,
                    reaction_id=reaction_id,
                    reaction_type=reaction_type,
                ),
            )
        except MapperApiError as e:
            raise ReactionError("add reaction failed") from e

    async def remove_reaction(
        self,
        chat_id: int,
        message_id: int | str,
    ) -> EmojiReaction | None:
        """Remove reaction.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_id: Identifier of the message.
        :type message_id: int | str
        :returns: The resulting EmojiReaction | None value.
        :rtype: EmojiReaction | None
        """

        return cast(
            EmojiReaction | None,
            await self(RemoveReactionMethod, chat_id=chat_id, message_id=message_id),
        )

    async def get_reactions(
        self,
        chat_id: int,
        message_ids: list[str] | list[int],
    ) -> dict[str, EmojiReaction] | None:
        """Retrieve reactions.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_ids: Identifiers of the messages.
        :type message_ids: list[str] | list[int]
        :returns: The resulting dict[<message_id>, <EmojiReaction for this message>] | None value.
        :rtype: dict[str, EmojiReaction] | None
        """

        return cast(
            dict[str, EmojiReaction] | None,
            await self(GetReactionsMethod, chat_id=chat_id, message_ids=message_ids),
        )

    async def read_message(
        self,
        chat_id: int,
        message_id: int | str,
        typeof: str = "READ_MESSAGE",
        mark: int | None = None,
    ) -> ReadState:
        """Read message.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_id: Identifier of the message.
        :type message_id: int | str
        :param typeof: Attachment class that determines the upload type.
        :type typeof: str
        :param mark: The mark value.
        :type mark: int | None
        :returns: The resulting ReadState value.
        :rtype: ReadState
        """

        return cast(
            ReadState,
            await self(
                ReadMessageMethod,
                chat_id=chat_id,
                message_id=message_id,
                typeof=typeof,
                mark=mark,
            ),
        )

    async def create_poll(
        self,
        poll: Poll,
    ) -> Poll:
        """Create poll.

        :param poll: Poll instance to process.
        :type poll: Poll
        :returns: The resulting Poll value what can be send with message in send_message method.
        :rtype: Poll
        """

        return cast(
            Poll,
            await self(
                CreatePollMethod,
                poll=poll,
            ),
        )

    async def vote_poll(
        self,
        chat_id: int,
        message_id: int | str,
        poll_id: int,
        answer_ids: list[int],
    ) -> PollState:
        """Submit a vote for poll.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_id: Identifier of the message.
        :type message_id: int | str
        :param poll_id: Identifier of the poll.
        :type poll_id: int
        :param answer_ids: Identifiers of the answer objects.
        :type answer_ids: list[int]
        :returns: The resulting PollState value.
        :rtype: PollState
        """

        return cast(
            PollState,
            await self(
                VotePollMethod,
                chat_id=chat_id,
                message_id=message_id,
                poll_id=poll_id,
                answer_ids=answer_ids,
            ),
        )
