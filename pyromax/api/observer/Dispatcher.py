import asyncio
from asyncio import Future
from socket import gaierror
import logging
from typing import Iterable

from websockets import WebSocketException

from .ObserverPattern import Subject
from .Router import Router
from pyromax.types import Update, Message, Opcode
from pyromax.api import MaxApi
from pyromax.utils import NotFoundFlag
from pyromax.utils import get_dict_value_by_path


class Dispatcher(Subject, Router):
    def __init__(self):
        super().__init__()

        self.__logger = logging.getLogger('MaxDispatcher')


    async def notify(self, update, data: dict):
        if not update:
            return
        for event in self.events.values():
            if event.opcode != update.opcode:
                continue
            handler = await event.update(update, data[MaxApi])
            if handler and event.event_name == update.type:
                args = [data[arg] for arg in handler.args if arg in data]
                await handler.function(*args)
                break


    async def _check_update(self, max_api: MaxApi):
        update = await max_api.max_client.wait_recv(cmd=0)
        update = Update(**(update[0]), max_api=max_api)
        data = {
            Opcode: update.opcode,
            Update: update,
        }
        data.update(max_api.base_data)


        self.__logger.debug(f'Dispatcher update: %s', update)
        for event in self.events.values():
            if event.opcode == update.opcode:

                parsed_update = event.type_of_update.from_update(update)
                data = parsed_update.edit_data(data)
                return parsed_update, data
        else:
            self.__logger.debug('Dispatcher update skipped: %s', update)
            return NotFoundFlag(), NotFoundFlag()


    async def start_polling(self, max_api: MaxApi):
        while True:
            if max_api.max_client:
                update, data = await self._check_update(max_api)
                await self.notify(update, data)
            else:
                raise WebSocketException('MaxApi.MaxClient instance not exist')

