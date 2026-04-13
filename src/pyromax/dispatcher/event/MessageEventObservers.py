from collections.abc import Callable
from typing import Any

from .StandardMaxEventObserver import StandardMaxEventObserver
from ...models import Message
from ...filters import Filter, FromMeFilter
from .Handler import Handler
from ...filters import MessageForwardFromFilter, ReplyToMessageFilter


class MessageEventObserver(StandardMaxEventObserver[Message]):

    def __call__(self, *filters: Filter, pattern: Callable[[Message], bool] | None = None, from_me: bool = False)\
            -> Callable[[Callable[..., Any]], None]:
        filters_list = []
        filters_list += list(filters)
        if not from_me:
            filters_list.append(~FromMeFilter())

        def decorator(func: Callable[..., Any]) -> None:
            handler = Handler(func, filters=filters_list, pattern=pattern)
            self.handlers.append(handler)
        return decorator

    async def is_my_update(
            self,
            update: Message
    ) -> bool:
        return await super().is_my_update(update) and update.status == self.event_name


class MessageForwardEventObserver(MessageEventObserver):
    async def is_my_update(
            self,
            update: Message
    ) -> bool:
        forward_filter = MessageForwardFromFilter()
        return await StandardMaxEventObserver.is_my_update(self, update) and bool(await forward_filter(update, data={Message: update}))


class ReplyToMessageEventObserver(MessageEventObserver):
    async def is_my_update(
            self,
            update: Message
    ) -> bool:
        reply_filter = ReplyToMessageFilter()
        return await StandardMaxEventObserver.is_my_update(self, update) and bool(await reply_filter(update, data={Message: update}))


