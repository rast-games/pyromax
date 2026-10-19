from typing import Literal, cast, overload

from .Base import BaseMaxApiMethod
from ..models.Chat import Chat
from ..models.Message import Message


FetchCommentsResult = (
    list[Message]
    | list[int | str]
    | tuple[list[Message] | list[int | str], Chat | None]
)


class FetchCommentsMethod(BaseMaxApiMethod[FetchCommentsResult]):
    @overload
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        from_: int | None = ...,
        backward: int = ...,
        get_messages: Literal[True] = True,
        forward: int = ...,
        get_chat: Literal[False] = False,
    ) -> list[Message]: ...

    @overload
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        from_: int | None = ...,
        backward: int = ...,
        get_messages: Literal[True] = True,
        forward: int = ...,
        get_chat: Literal[True] = True,
    ) -> tuple[list[Message], Chat | None]: ...

    @overload
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        from_: int | None = ...,
        backward: int = ...,
        get_messages: Literal[False] = False,
        forward: int = ...,
        get_chat: Literal[False] = False,
    ) -> list[int | str]: ...

    @overload
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        from_: int | None = ...,
        backward: int = ...,
        get_messages: Literal[False] = False,
        forward: int = ...,
        get_chat: Literal[True] = True,
    ) -> tuple[list[int | str], Chat | None]: ...

    @overload
    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        from_: int | None = ...,
        backward: int = ...,
        get_messages: bool = ...,
        forward: int = ...,
        get_chat: bool = ...,
    ) -> FetchCommentsResult: ...

    async def __call__(
        self,
        chat_id: int,
        post_id: int,
        from_: int | None = None,
        backward: int = 30,
        get_messages: bool = True,
        forward: int = 0,
        get_chat: bool = False,
    ) -> FetchCommentsResult:
        """Fetch comments for a channel post."""
        if not self._max_api:
            raise RuntimeError("FetchComments method not bound to MaxApi instance")

        return cast(
            FetchCommentsResult,
            await self._max_api.mapper.call_method(
                type(self),
                chat_id=chat_id,
                post_id=post_id,
                from_=from_,
                backward=backward,
                get_messages=get_messages,
                forward=forward,
                get_chat=get_chat,
            ),
        )
