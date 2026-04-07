from collections.abc import Callable

from .StandardMaxEventObserver import StandardMaxEventObserver
from ...models import Message
from ...filters import Filter, FromMeFilter
from .Handler import Handler
from ...filters import MessageForwardFromFilter, ReplyToMessageFilter


class MessageEventObserver(StandardMaxEventObserver[Message]):

    def __call__(self, *filters: Filter, pattern: Callable[[Message], bool] = None, from_me: bool = False):
        if not from_me:
            filters = list(filters)
            filters.append(~FromMeFilter())

        def decorator(func):
            handler = Handler(func, filters=filters, pattern=pattern)
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
        return await StandardMaxEventObserver.is_my_update(self, update) and await forward_filter(update, data={Message: update})


class ReplyToMessageEventObserver(MessageEventObserver):
    async def is_my_update(
            self,
            update: Message
    ) -> bool:
        reply_filter = ReplyToMessageFilter()
        return await StandardMaxEventObserver.is_my_update(self, update) and await reply_filter(update, data={Message: update})


