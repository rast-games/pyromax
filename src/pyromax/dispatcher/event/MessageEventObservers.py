from collections.abc import Callable

from .StandardMaxEventObserver import StandardMaxEventObserver
from src.pyromax.models import Message
from src.pyromax.filters import Filter, FromMeFilter
from .Handler import Handler


class MessageEventObserver(StandardMaxEventObserver[Message]):

    def __call__(self, *filters: Filter, pattern: Callable[[Message], bool] = None, from_me: bool = False):
        if not from_me:
            filters = list(filters)
            filters.append(~FromMeFilter())

        def decorator(func):
            handler = Handler(func, filters=filters, pattern=pattern)
            self.handlers.append(handler)
        return decorator

    def is_my_update(
            self,
            update: Message
    ) -> bool:
        return super().is_my_update(update) and update.status == self.event_name



class ReplyToMessageEventObserver(MessageEventObserver):
    def is_my_update(
            self,
            update: Message
    ) -> bool:
        return super().is_my_update(update) and (update.link.type == self.event_name if update.link else None)