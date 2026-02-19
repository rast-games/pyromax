from collections.abc import Generator
from typing import List, Optional

from pyromax.api.observer.event import MaxEventObserver
from pyromax.api.observer import ObserverPattern
from pyromax.api import MaxApi
from pyromax.types import (
    Message,
    MessageReactionUpdate,
    Opcode, Update
)


class Router(ObserverPattern.Subject):
    def __init__(self):
        self.sub_routers: list[Router] = []
        self._parent_router = None

        self.message = MaxEventObserver(self, 'USER', opcode=Opcode.PUSH_NOTIFICATION.value, type_of_update=Message)
        self.edited_message = MaxEventObserver(self, 'EDITED_MESSAGE', opcode=Opcode.PUSH_NOTIFICATION.value, type_of_update=Message)
        self.reply_to_message = MaxEventObserver(self, 'REPLY', opcode=Opcode.PUSH_NOTIFICATION.value, type_of_update=Message)
        self.message_added_reaction = MaxEventObserver(self, 'MESSAGE_ADDED_REACTION', opcode=Opcode.MESSAGE_REACTION_UPDATE.value, type_of_update=MessageReactionUpdate)
        self.message_deleted_reaction = MaxEventObserver(self, 'MESSAGE_DELETED_REACTION', opcode=Opcode.MESSAGE_REACTION_UPDATE.value, type_of_update=MessageReactionUpdate)
        self.events = {
            'MESSAGE': self.message,
            'EDITED_MESSAGE': self.edited_message,
            'REPLY_TO_MESSAGE': self.reply_to_message,
            'MESSAGE_ADDED_REACTION': self.message_added_reaction,
            'MESSAGE_DELETED_REACTION': self.message_deleted_reaction,
        }



    @property
    def chain_head(self) -> Generator['Router', None, None]:
        router: Router | None = self
        print(self.sub_routers)
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

    async def notify(self, update: Update, data = None) -> None:
        if data is None:
            raise ValueError("data cannot be None")

        for event in self.events.values():
            if event.opcode != update.opcode:
                continue
            handler, data = await event.update(update, data[MaxApi], data=data)
            if handler and event.event_name == update.type:
                args = [data[arg] for arg in handler.args if arg in data]
                return await handler.function(*args)

        for router in self.sub_routers:
            return await router.notify(update=update, data=data)
            # router.notify(update=update, data=data)


    # def include_router(self, router):
    #     for name, event in self.events.items():
    #         event: MaxEventObserver
    #         event.include_event(router.events.pop(name))
    #
    #
    # def include_routers(self, routers):
    #     for router in routers:
    #         self.include_router(router)
