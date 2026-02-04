from typing import List
from pyromax.api.observer.event import MaxEventObserver

from pyromax.types import Opcode


class Router:
    def __init__(self):
        self._allowed_args_for_handler = {}


        self.message = MaxEventObserver(self, 'USER', opcode=Opcode.PUSH_NOTIFICATION.value)
        self.edited_message = MaxEventObserver(self, 'EDITED', opcode=Opcode.PUSH_NOTIFICATION.value)
        self.events = {
            'MESSAGE': self.message,
            'USER': self.edited_message,
        }

        # for name, event in self.events.items():
        #     self.__dict__[name] = event

        # from pprint import pprint
        # pprint(self.__dict__)


    def include_router(self, router):
        for name, event in self.events.items():
            event: MaxEventObserver
            event.include_event(router.events.pop(name))


    def include_routers(self, routers):
        for router in routers:
            self.include_router(router)
