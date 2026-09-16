from __future__ import annotations
import logging
from collections.abc import Sequence, Iterable
from typing import TYPE_CHECKING, Any, cast, overload, Literal
from collections.abc import Callable, Coroutine
import time
import asyncio

from ..payloads.models import (
    BaseFileMappingModel,
    ReadStateMappingModel,
    PollMappingModel,
)
from .....protocol.envelope import Envelope, EnvelopeProtocol
from ..constants import DEFAULT_BACKOFF_CONFIG
from .....utils import clean_and_map, Backoff
from ..methods.immutable import (
    SendMessageMethod,
    EditMessageMethod,
    GetMessagesMethod,
    GetChatHistoryMethod,
    DeleteMessageMethod,
    PinMessageMethod,
    AddReactionMethod,
    RemoveReactionMethod,
    GetReactionsMethod,
    ReadMessageMethod,
    VotePollMethod,
)
from .....exceptions import (
    SendMessageFileError,
    SendMessageNotFoundError,
    SendMessageError,
    BackoffError,
    MapperApiError,
    ReactionMapperError,
    BaseTransportError,
)
from ..payloads.responses import (
    SendMessageResponse,
    EditMessageResponse,
    GetMessagesResponse,
    GetChatHistoryResponse,
    GetChatHistoryMessagesResponse,
    GetChatHistoryMessagesIdsResponse,
    AddOrRemoveReactionResponse,
    GetReactionsResponse,
    VoteStateContainsResponse,
)
from ..translate.ToDTO import translate_models
from ..translate.FromDTO import reverse_translate_poll
from .....models import Message, EmojiReaction, ReadState, Poll, PollState, Chat

from .MixinProtocol import MixinProtocol

from .....models import MessageLink

if TYPE_CHECKING:
    pass


class MessageMixin(MixinProtocol):
    async def send_message(
        self,
        chat_id: int,
        text: str | None = None,
        attaches: Sequence[BaseFileMappingModel] | None = None,
        link: MessageLink | None = None,
        parse_tags: bool = True,
        notify: bool = True,
        **kwargs: Any,
    ) -> Message | None:
        """Send a message through the envelope mapper.

        :raises SendMessageError: If MAX rejects the message or it cannot be sent.


        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param text: Message or textual content.
        :type text: str | None
        :param attaches: Attachments associated with the message.
        :type attaches: Sequence[BaseFileMappingModel] | None
        :param link: Invite, message, or resource link.
        :type link: MessageLink | None
        :param parse_tags: The parse tags value.
        :type parse_tags: bool
        :param notify: Whether MAX should notify affected users.
        :type notify: bool
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting Message | None value.
        :rtype: Message | None
        :raises SendMessageFileError: If the requested action cannot be completed.
        :raises SendMessageNotFoundError: If the requested action cannot be completed.
        """
        original_attaches = attaches
        if not attaches:
            attaches = []
        attachments = []
        for attach in attaches:
            if hasattr(attach, "is_attach") and attach.is_attach:
                attachments.extend(attach.to_payload)
        backoff = Backoff(config=DEFAULT_BACKOFF_CONFIG)
        if "elements" in kwargs:
            elements = kwargs["elements"]
        else:
            elements = []

        if parse_tags:
            text, _elements = clean_and_map(
                text if text else "",
                ["STRONG", "EMPHASIZED", "UNDERLINE", "STRIKETHROUGH", "QUOTE", "LINK"],
            )
            elements += _elements
        try:
            response = await self.send(
                method=SendMessageMethod(
                    chat_id=chat_id,
                    text=text,
                    cid=-round(time.time() * 1000),
                    attaches=attachments,
                    elements=elements,
                    link=link,
                    notify=notify,
                ),
            )

            try:
                while (
                    error_if_exist := response.model_dump()
                    .get("payload", {})
                    .get("error")
                ):
                    error_message = (
                        response.model_dump().get("payload", {}).get("message")
                    )
                    title = response.model_dump().get("payload", {}).get("title")
                    match error_if_exist:
                        case "attachment.not.ready":
                            response = await self.send(
                                method=SendMessageMethod(
                                    chat_id=chat_id,
                                    text=text,
                                    cid=-round(time.time() * 1000),
                                    attaches=attachments,
                                    elements=elements,
                                    link=link,
                                ),
                            )
                            await backoff.asleep()
                            continue
                        case "proto.payload":
                            raise SendMessageFileError(f"""
                                title: {title},
                                error: {error_if_exist},
                                message: {error_message}
                                """)
                        case "not.found":
                            raise SendMessageNotFoundError(f"""
                                title: {title},
                                error: {error_if_exist},
                                message: {error_message}
                                """)
                        case _:
                            raise SendMessageError(f"""
                                title: {title},
                                error: {error_if_exist},
                                message: {error_message}
                                """)
            except BackoffError:
                raise SendMessageError("Max attempts to send message exceeded")
            response_parsed = SendMessageResponse(**response.payload)
            for attach in response_parsed.message.attaches:
                if hasattr(attach, "is_attach") and attach.is_attach:
                    attach.message_id = response_parsed.message.id
                    attach.chat_id = response_parsed.chat_id
                    attach.uploaded = True
            for i, attach in enumerate(original_attaches or []):
                if (
                    hasattr(attach, "is_attach")
                    and attach.is_attach
                    and hasattr(attach, "is_downloadable")
                    and attach.is_downloadable
                ):
                    recv_attach = response_parsed.message.attaches[i]
                    for attr, value in recv_attach.__dict__.items():
                        if hasattr(attach, attr):
                            setattr(attach, attr, value)
            mapped_message = response_parsed.message
            mapped_message.chat_id = response_parsed.chat_id
            translated_message = cast(
                Message,
                translate_models(
                    mapped_message, fallback_chat_id=response_parsed.chat_id
                ),
            )

            self.bind_api_instance(translated_message)
            return translated_message

        except (
            asyncio.CancelledError,
            BaseTransportError,
        ) as e:
            self._logger.error("Error sending message: %s", e)
            return None
            # raise SendMessageError(
            #     'Transport error while sending message or bot was cancelled'
            # )

    async def forward_message(
        self,
        message_id: int | str,
        to_chat_id: int,
        from_chat_id: int,
        notify: bool = True,
    ) -> Message | None:
        """Websocket can work with both message id types(str | int), but browser uses str, and if you want mask the use
        userbot, should use str type

        Socket use only int, and server raise exception if you try to send message ids use str type

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
        """

        # if isinstance(message_id, int):
        #     msg_id = str(message_id)

        link = MessageLink(
            type="FORWARD",
            message_id=message_id,
            chat_id=from_chat_id,
        )

        return await self.send_message(
            chat_id=to_chat_id,
            link=link,
            notify=notify,
        )

    async def edit_message(
        self,
        chat_id: int,
        message_id: int | str,
        text: str | None = None,
        attaches: Sequence[BaseFileMappingModel] | None = None,
        parse_tags: bool = True,
        **kwargs: Any,
    ) -> Message:
        """Websocket can work with both message id types(str | int), but browser uses str, and if you want mask the use
        userbot, should use str type

        Socket use only int, and server raise exception if you try to send message ids use str type

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_id: Identifier of the message.
        :type message_id: int | str
        :param text: Message or textual content.
        :type text: str | None
        :param attaches: Attachments associated with the message.
        :type attaches: Sequence[BaseFileMappingModel] | None
        :param parse_tags: The parse tags value.
        :type parse_tags: bool
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting Message value.
        :rtype: Message
        """

        if not attaches:
            attaches = []
        if "elements" in kwargs:
            elements = kwargs["elements"]
        else:
            elements = []

        attachments = []
        for attach in attaches:
            if hasattr(attach, "is_attach") and attach.is_attach:
                attachments.extend(attach.to_payload)

        if parse_tags:
            text, _elements = clean_and_map(
                text if text else "",
                ["STRONG", "EMPHASIZED", "UNDERLINE", "STRIKETHROUGH", "QUOTE", "LINK"],
            )
            elements += _elements

        response = await self.send(
            method=EditMessageMethod(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                elements=elements,
                attaches=attachments,
            ),
        )

        mapped_edited_message = EditMessageResponse(**response.payload).message

        edited_message = cast(
            Message,
            translate_models(mapped_edited_message),
        )
        edited_message.chat_id = chat_id

        return self.bind_api_instance(edited_message)

    async def get_messages(
        self,
        chat_id: int,
        message_ids: Iterable[str] | Iterable[int],
    ) -> list[Message]:
        """Websocket can work with both message id types(str | int), but browser uses str, and if you want mask the use
        userbot, should use str type

        Socket use only int, and server raise exception if you try to send message ids use str type

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_ids: Identifiers of the messages.
        :type message_ids: Iterable[str] | Iterable[int]
        :returns: The resulting collection.
        :rtype: list[Message]
        """

        # msg_ids = [str(msg_id) for msg_id in message_ids]
        response = await self.send(
            method=GetMessagesMethod(
                chat_id=chat_id,
                message_ids=message_ids,
            )
        )

        mapped_messages = GetMessagesResponse(**response.payload)
        for message in mapped_messages.messages:
            message.chat_id = mapped_messages.chat_id
        messages = [translate_models(message) for message in mapped_messages.messages]

        msgs = cast(list[Message], messages)

        return [self.bind_api_instance(message) for message in msgs]

    @overload
    async def get_chat_history(
        self,
        chat_id: int,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = ...,
        item_type: str = ...,
        get_chat: Literal[False] = False,
        get_messages: Literal[True] = True,
        interactive: bool = ...,
    ) -> list[Message]:
        """Retrieve chat history.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param forward: The forward value.
        :type forward: int
        :param backward: The backward value.
        :type backward: int
        :param backward_time: The backward time value.
        :type backward_time: int
        :param forward_time: The forward time value.
        :type forward_time: int
        :param from_time: The from time value.
        :type from_time: int | None
        :param item_type: The item type value.
        :type item_type: str
        :param get_chat: The get chat value.
        :type get_chat: bool
        :param get_messages: Literal[True] instance to process.
        :type get_messages: Literal[True]
        :param interactive: The interactive value.
        :type interactive: bool
        :returns: The resulting collection.
        :rtype: list[Message]
        """
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
        item_type: str = ...,
        get_chat: Literal[True] = True,
        get_messages: Literal[True] = True,
        interactive: bool = ...,
    ) -> tuple[list[Message], Chat | None]: ...

    @overload
    async def get_chat_history(
        self,
        chat_id: int,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = ...,
        item_type: str = ...,
        get_chat: Literal[False] = False,
        get_messages: Literal[False] = False,
        interactive: bool = ...,
    ) -> list[str | int]:
        """Retrieve chat history.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param forward: The forward value.
        :type forward: int
        :param backward: The backward value.
        :type backward: int
        :param backward_time: The backward time value.
        :type backward_time: int
        :param forward_time: The forward time value.
        :type forward_time: int
        :param from_time: The from time value.
        :type from_time: int | None
        :param item_type: The item type value.
        :type item_type: str
        :param get_chat: The get chat value.
        :type get_chat: bool
        :param get_messages: Literal[False] instance to process.
        :type get_messages: Literal[False]
        :param interactive: The interactive value.
        :type interactive: bool
        :returns: The resulting collection.
        :rtype: list[str | int]
        """
        ...

    @overload
    async def get_chat_history(
        self,
        chat_id: int,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = ...,
        item_type: str = ...,
        get_chat: Literal[True] = True,
        get_messages: Literal[False] = False,
        interactive: bool = ...,
    ) -> tuple[list[str | int], Chat | None]: ...

    @overload
    async def get_chat_history(
        self,
        chat_id: int,
        forward: int = ...,
        backward: int = ...,
        backward_time: int = ...,
        forward_time: int = ...,
        from_time: int | None = ...,
        item_type: str = ...,
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
        item_type: str = "REGULAR",
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
        :param forward: The forward value.
        :type forward: int
        :param backward: The backward value.
        :type backward: int
        :param backward_time: The backward time value.
        :type backward_time: int
        :param forward_time: The forward time value.
        :type forward_time: int
        :param from_time: The from time value.
        :type from_time: int | None
        :param item_type: The item type value.
        :type item_type: str
        :param get_chat: The get chat value.
        :type get_chat: bool
        :param get_messages: The get messages value.
        :type get_messages: bool
        :param interactive: The interactive value.
        :type interactive: bool
        :returns: History items, paired with the requested chat when ``get_chat`` is true.
        :rtype: list[Message] | list[str | int] | tuple[list[Message] | list[str | int], Chat | None]
        :raises MapperApiError: If server return unknown response different from expected.
        """
        response = await self.send(
            method=GetChatHistoryMethod(
                chat_id=chat_id,
                forward=forward,
                backward=backward,
                backward_time=backward_time,
                forward_time=forward_time,
                from_time=from_time or int(time.time() * 1000),
                item_type=item_type,
                get_chat=get_chat,
                get_messages=get_messages,
                interactive=interactive,
            )
        )

        mapped_messages = GetChatHistoryResponse(payload=response.payload)
        chat = None
        if mapped_messages.payload.chat is not None:
            chat = cast(Chat, translate_models(mapped_messages.payload.chat))

        if get_messages:
            if not isinstance(mapped_messages.payload, GetChatHistoryMessagesResponse):
                raise MapperApiError(
                    "server return unknown response different from expected"
                )
            for message in mapped_messages.payload.messages:
                message.chat_id = chat_id

            messages = [
                translate_models(message)
                for message in mapped_messages.payload.messages
            ]

            msgs = cast(list[Message], messages)
            if get_chat:
                return [self.bind_api_instance(message) for message in msgs] or [], chat
            return [self.bind_api_instance(message) for message in msgs] or []
        if not isinstance(mapped_messages.payload, GetChatHistoryMessagesIdsResponse):
            raise MapperApiError(
                "server return unknown response different from expected"
            )
        if get_chat:
            return mapped_messages.payload.message_ids or [], chat
        return mapped_messages.payload.message_ids or []

    async def delete_messages(
        self, chat_id: int, message_ids: list[str] | list[int], for_me: bool = False
    ) -> None:
        """Websocket can work with both message id types(str | int), but browser uses str, and if you want mask the use
        userbot, should use str type

        Socket use only int, and server raise exception if you try to send message ids use str type

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_ids: Identifiers of the messages.
        :type message_ids: list[str] | list[int]
        :param for_me: The for me value.
        :type for_me: bool
        """

        await self.send(
            method=DeleteMessageMethod(
                chat_id=chat_id,
                message_ids=message_ids,
                for_me=for_me,
            )
        )

        return None

    async def pin_message(
        self,
        chat_id: int,
        pin_message_id: int | str,
        notify_pin: bool = True,
    ) -> None:
        """Websocket can work with both message id types(str | int), but browser uses str, and if you want mask the use
        userbot, should use str type

        Socket use only int, and server raise exception if you try to send message ids use str type

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param pin_message_id: Identifier of the pin message.
        :type pin_message_id: int | str
        :param notify_pin: The notify pin value.
        :type notify_pin: bool
        """

        await self.send(
            method=PinMessageMethod(
                chat_id=chat_id, pin_message_id=pin_message_id, notify_pin=notify_pin
            )
        )
        return None

    async def add_reaction(
        self,
        chat_id: int,
        message_id: int | str,
        reaction_id: str,
        reaction_type: str = "EMOJI",
    ) -> EmojiReaction | None:
        """Websocket can work with both message id types(str | int), but browser uses str, and if you want mask the use
        userbot, should use str type

        Socket use only int, and server raise exception if you try to send message ids use str type

        :param chat_id: int
        :type chat_id: int
        :param message_id: int | str
        :type message_id: int | str
        :param reaction_id: str
        :type reaction_id: str
        :param reaction_type: str
        :type reaction_type: str

        :returns: info about reaction or None if cannot get this info
        :rtype: EmojiReaction | None

        :raises ReactionMapperError: if adding reaction failed
        """

        try:
            response = await self.send(
                method=AddReactionMethod(
                    chat_id=chat_id,
                    message_id=message_id,
                    reaction_id=reaction_id,
                    reaction_type=reaction_type,
                ),
                check_errors=True,
            )
        except MapperApiError as e:
            if e.error == "error.message.like.unknown.reaction":
                raise ReactionMapperError(
                    f"Your reaction_id is not supported by server"
                ) from e
            raise ReactionMapperError(
                "Unknown error while adding reaction to message"
            ) from e

        mapped_reaction_info = AddOrRemoveReactionResponse(
            **response.payload
        ).reaction_info

        if mapped_reaction_info is None:
            return None

        reaction_info = cast(
            EmojiReaction,
            translate_models(
                mapped_reaction_info,
                chat_id=chat_id,
                message_id=message_id,
                status="ADD",
            ),
        )

        return reaction_info

    async def remove_reaction(
        self,
        chat_id: int,
        message_id: str | int,
    ) -> EmojiReaction | None:
        """Remove reaction.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param message_id: Identifier of the message.
        :type message_id: str | int
        :returns: The resulting EmojiReaction | None value.
        :rtype: EmojiReaction | None
        """
        response = await self.send(
            method=RemoveReactionMethod(
                chat_id=chat_id,
                message_id=message_id,
            )
        )
        mapped_reaction_info = AddOrRemoveReactionResponse(
            **response.payload
        ).reaction_info

        if mapped_reaction_info is None:
            return None

        reaction_info = cast(
            EmojiReaction,
            translate_models(
                mapped_reaction_info,
                chat_id=chat_id,
                message_id=message_id,
                status="REMOVE",
            ),
        )

        return self.bind_api_instance(reaction_info)

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
        :returns: The resulting dict[str, EmojiReaction] | None value.
        :rtype: dict[str, EmojiReaction] | None
        """
        response = await self.send(
            method=GetReactionsMethod(
                chat_id=chat_id,
                message_ids=message_ids,
            ),
        )

        mapped_messages_reactions = GetReactionsResponse(
            **response.payload
        ).messages_reactions
        if mapped_messages_reactions is None:
            return None

        res = cast(
            dict[str, EmojiReaction],
            {
                message_id: translate_models(
                    reaction_info, chat_id=chat_id, message_id=message_id
                )
                for message_id, reaction_info in mapped_messages_reactions.items()
            },
        )

        [self.bind_api_instance(reaction) for reaction in res.values()]

        return res

    async def read_message(
        self,
        chat_id: int,
        message_id: int | str,
        typeof: str,
        mark: int | None = None,
    ) -> ReadState:
        """Websocket can work with both message id types(str | int), but browser uses str, and if you want mask the use
        userbot, should use str type

        Socket use only int, and server raise exception if you try to send message ids use str type

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

        if mark is None:
            mark = int(time.time() * 1000)
        response = await self.send(
            method=ReadMessageMethod(
                chat_id=chat_id,
                message_id=message_id,
                type=typeof,
                mark=mark,
            )
        )

        mapped_read_state = ReadStateMappingModel(**response.payload)

        read_state = cast(
            ReadState,
            translate_models(
                mapped_read_state,
                chat_id=chat_id,
                message_id=message_id,
            ),
        )

        return self.bind_api_instance(read_state)

    async def create_poll(self, poll: Poll[None]) -> PollMappingModel:
        """Create poll.

        :param poll: Poll[None] instance to process.
        :type poll: Poll[None]
        :returns: The resulting PollMappingModel value.
        :rtype: PollMappingModel
        """
        return reverse_translate_poll(poll)

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
        :raises MapperApiError: If server dont return poll state.
        """
        response = await self.send(
            method=VotePollMethod(
                chat_id=chat_id,
                message_id=message_id,
                poll_id=poll_id,
                answer_ids=answer_ids,
            )
        )

        mapped_poll_state = VoteStateContainsResponse(**response.payload)
        if mapped_poll_state is None:
            raise MapperApiError("Server dont return poll state")

        poll_state = cast(PollState, translate_models(mapped_poll_state))
        return self.bind_api_instance(poll_state)
