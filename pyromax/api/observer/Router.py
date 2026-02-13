from typing import List
from pyromax.api.observer.event import MaxEventObserver

from pyromax.types import Opcode
from pyromax.types import (
Message,
MessageReactionUpdate
)


class Router:
    def __init__(self):

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


    def include_router(self, router):
        for name, event in self.events.items():
            event: MaxEventObserver
            event.include_event(router.events.pop(name))


    def include_routers(self, routers):
        for router in routers:
            self.include_router(router)
