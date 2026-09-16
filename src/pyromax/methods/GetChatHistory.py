from typing import Union, overload, cast, Literal

from .Base import BaseMaxApiMethod
from ..models.Chat import Chat
from ..models.Message import Message


class GetChatHistoryMethod(
    BaseMaxApiMethod[
        Union[
            list[Message],
            list[str | int],
            tuple[Union[list[Message], list[str | int]], Union[Chat, None]],
        ]
    ]
):
    @overload
    async def __call__(
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
        """Execute the get chat history MAX API method.

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
    async def __call__(
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
    async def __call__(
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
        """Execute the get chat history MAX API method.

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
        pass

    @overload
    async def __call__(
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
    async def __call__(
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

    async def __call__(
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
        """Execute the get chat history MAX API method.

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
        :raises RuntimeError: If getChatHistory method not bound to MaxApi instance.
        """
        if not self._max_api:
            raise RuntimeError("GetChatHistory method not bound to MaxApi instance")

        return cast(
            list[Message]
            | list[str | int]
            | tuple[list[Message] | list[str | int], Chat | None],
            await self._max_api.mapper.call_method(
                type(self),
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
