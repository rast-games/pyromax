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
    Update, UNHANDLED, UNKNOWN_UPDATE, StandardMaxEventObserver, UpdateMaxEventObserver
)
from ..models import EmojiReaction, Message, ErrorEvent, BaseMaxObject, DataDict
from ..protocol.bases import Response


class Router(Subject):
    """Container for handlers and nested routers.

    Routers group event handlers into reusable modules and allow
    hierarchical composition of bot logic.

    Attributes:
        events: a dict with all event observers(listeners)

    """
    def __init__(self, handlers_can_skip_yourself_when_return_unhandled: bool = False) -> None:
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
        self.error = StandardMaxEventObserver(self, 'ERROR', type_of_update=ErrorEvent)
        # self.raw_update = UpdateMaxEventObserver(self, 'RAW_UPDATE', type_of_update=Response)
        self.events: dict[str, StandardMaxEventObserver[Any]] = {
            'EDITED': self.edited_message,
            'REPLY': self.reply_to_message,
            'FORWARD': self.forward_message,
            'REMOVED': self.message_removed,
            'USER': self.message,
            'MESSAGE_ADDED_REACTION': self.message_added_reaction,
            'MESSAGE_DELETED_REACTION': self.message_deleted_reaction,
            'MESSAGE_REACTION': self.message_reaction,
            'ERROR': self.error,
            # 'RAW_UPDATE': self.raw_update,
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
        """Attach multiple child routers at once.

        Parameters
        ----------
        routers
            Routers to attach.
        """
        if not routers:
            msg = "At least one router must be provided"
            raise ValueError(msg)
        for router in routers:
            self.include_router(router)

    def include_router(self, router: 'Router') -> 'Router':
        """Attach another router as a child router.

        Parameters
        ----------
        router
            Router to attach.

        Returns
        -------
        Router
            The attached router.
        """
        if not isinstance(router, Router):
            msg = f"router should be instance of Router not {type(router).__class__.__name__}"
            raise ValueError(msg)
        router.parent_router = self
        return router

    async def notify(self, update: Update, data: dict[Any, Any] | None = None, event_types: list[str] | None = None) -> Any:
        """Propagate an update through handlers and child routers.

           Parameters
           ----------
           update
               Incoming update object.
           data
               Context data available to handlers.
           event_types
               keys of Router.events

           Returns
           -------
           bool
               Any if the update was handled, otherwise UNHANDLED.
           """

        if event_types is None:
            event_types = []
        
        if data is None:
            raise ValueError("data cannot be None")

        unknown_update = False

        for key, event in self.events.items():
            if await event.is_my_update(update):
                if key not in event_types:
                    event_types.append(key)
        if not event_types:
            unknown_update = True

        response = UNHANDLED

        for event_type in event_types:
            observer = self.events.get(event_type)
            if observer:
                result = await observer.check_root_filters(update, data)
                if not result:
                    continue
                response = await observer.wrap_outer_middleware(
                    observer.update,
                    update,
                    data=data
                )
                if response is not UNHANDLED:
                    return response

        if not self.sub_routers and unknown_update:
            return UNKNOWN_UPDATE

        if not self.sub_routers and not unknown_update:
            return UNHANDLED

        update_type_in_sub_routers = False
        for router in self.sub_routers:
            response = await router.notify(update=update, data=data, event_types=event_types)
            if response is UNHANDLED:
                update_type_in_sub_routers = True

            if response is not UNHANDLED and response is not UNKNOWN_UPDATE:
                return response
        else:
            if update_type_in_sub_routers:
                return UNHANDLED
            return UNKNOWN_UPDATE
