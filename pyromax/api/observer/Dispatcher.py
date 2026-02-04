from socket import gaierror
import logging
from typing import Iterable


from .ObserverPattern import Subject
from .Router import Router
from pyromax.types import Update, Message, Opcode
from pyromax.api import MaxApi
from pyromax.utils import NotFoundFlag
from pyromax.utils import get_dict_value_by_path


class Dispatcher(Subject, Router):
    def __init__(self):
        super().__init__()
        # self._allowed_args_for_handler = {
        #     MaxApi: None,
        #     Update: None,
        #     Message: None,
        # }
        self.__logger = logging.getLogger('MaxDispatcher')


    async def notify(self, update, data: dict):
        if not update:
            return
        from pprint import pprint
        # pprint(self.events['message'].handlers)
        for event in self.events.values():
            handler = await event.update(update, data[MaxApi])
            if handler and event.event_name == update.type:
                args = [data[arg] for arg in handler.args if arg in data]
                await handler.function(*args)
                break


    async def _check_update(self, max_api: MaxApi):
        if not max_api.max_client._wait_recv:
            update: list[Update] = await max_api.max_client.wait_recv(return_updates=True)
            dumped_update = update[0].model_dump()
            if not update or update[0].opcode not in (event.opcode for event_name, event in self.events.items()):
                # dev заглушка, пока чиню все это
                return NotFoundFlag(), NotFoundFlag()
            update = Message.from_update(update[0])
            data = {
                Opcode: update.opcode,
                Message: update,
            }
            data.update(max_api.base_data)
            self.__logger.debug(f'Dispatcher update: %s', update)
            if update.opcode == Opcode.PUSH_NOTIFICATION.value:
                self.__logger.debug('PUSH_NOTIFICATION')
                return update, data
            self.__logger.debug('Dispatcher update skipped: %s', update)
        return NotFoundFlag(), NotFoundFlag()


    async def start_polling(self, max_api: MaxApi):
        max_api.max_client.update_fallback = self.notify
        while True:
            if max_api.max_client:
                update, data = await self._check_update(max_api)
                await self.notify(update, data)

