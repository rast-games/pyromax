from collections.abc import Generator
from typing import Optional, Any

from .ObserverPattern import Subject
from .event import (
    MessageEventObserver,
    ReplyToMessageEventObserver,
    MessageForwardEventObserver,
    RemovedMessageEventObserver,
    EmojiReactionAddObserver,
    EmojiReactionRemoveObserver,
    Update, StandardMaxEventObserver,
)
from ..models import EmojiReaction, Message, BaseMaxObject


class Router(Subject):
    def __init__(self) -> None:
        self.sub_routers: list[Router] = []
        self._parent_router: None | Router = None



        self.message = MessageEventObserver(self, 'USER', type_of_update=Message)
        self.message_removed = RemovedMessageEventObserver(self, 'REMOVED', type_of_update=Message)
        self.edited_message = MessageEventObserver(self, 'EDITED', type_of_update=Message)
        self.reply_to_message = ReplyToMessageEventObserver(self, 'REPLY', type_of_update=Message)
        self.forward_message = MessageForwardEventObserver(self, 'FORWARD', type_of_update=Message)
        self.message_reaction = StandardMaxEventObserver(self, 'MESSAGE_REACTION', type_of_update=EmojiReaction)
        self.message_added_reaction = EmojiReactionAddObserver(self, 'MESSAGE_ADDED_REACTION', type_of_update=EmojiReaction)
        self.message_deleted_reaction = EmojiReactionRemoveObserver(self, 'MESSAGE_DELETED_REACTION', type_of_update=EmojiReaction)
        self.events: dict[str, StandardMaxEventObserver[Any]] = {
            'EDITED_MESSAGE': self.edited_message,
            'REPLY_TO_MESSAGE': self.reply_to_message,
            'FORWARD_MESSAGE': self.forward_message,
            'MESSAGE_REMOVED': self.message_removed,
            'MESSAGE': self.message,
            'MESSAGE_ADDED_REACTION': self.message_added_reaction,
            'MESSAGE_DELETED_REACTION': self.message_deleted_reaction,
            'MESSAGE_REACTION': self.message_reaction,
        }



    @property
    def chain_head(self) -> Generator['Router', None, None]:
        router: Router | None = self
        while router:
            yield router
            router = router.parent_router

    @property
    def chain_tail(self) -> Generator['Router', None, None]:
        yield self
        for router in self.sub_routers:
            yield from router.chain_tail

    @property
    def parent_router(self) -> Optional['Router']:
        return self._parent_router

    @parent_router.setter
    def parent_router(self, router: 'Router') -> None:
        """
        Internal property setter of parent router fot this router.
        Do not use this method in own code.
        All routers should be included via `include_router` method.

        Self- and circular- referencing are not allowed here

        :param router:
        """
        if not isinstance(router, Router):
            msg = f"router should be instance of Router not {type(router).__name__!r}"
            raise ValueError(msg)
        if self._parent_router:
            msg = f"Router is already attached to {self._parent_router!r}"
            raise RuntimeError(msg)
        if self == router:
            msg = "Self-referencing routers is not allowed"
            raise RuntimeError(msg)

        parent: Router | None = router
        while parent is not None:
            if parent == self:
                msg = "Circular referencing of Router is not allowed"
                raise RuntimeError(msg)

            parent = parent.parent_router

        self._parent_router = router
        router.sub_routers.append(self)

    def include_routers(self, *routers: 'Router') -> None:
        """
        Attach multiple routers.

        :param routers:
        :return:
        """
        if not routers:
            msg = "At least one router must be provided"
            raise ValueError(msg)
        for router in routers:
            self.include_router(router)

    def include_router(self, router: 'Router') -> 'Router':
        """
        Attach another router.

        :param router:
        :return:
        """
        if not isinstance(router, Router):
            msg = f"router should be instance of Router not {type(router).__class__.__name__}"
            raise ValueError(msg)
        router.parent_router = self
        return router

    async def notify(self, update: Update, data: dict[Any, Any] | None = None) -> bool:
        if data is None:
            raise ValueError("data cannot be None")

        for event in self.events.values():
            if await event.is_my_update(update):
                handled = await event.update(update, data=data)
                if handled:
                    return True

        for router in self.sub_routers:
            handled = await router.notify(update=update, data=data)
            if handled:
                return True
        return False
