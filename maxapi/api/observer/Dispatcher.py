from socket import gaierror
import logging
from typing import Iterable
from pprint import pprint

from .ObserverPattern import Subject
from .Router import Router
from maxapi.types import Update, Opcode
from maxapi.api import MaxApi
from maxapi.utils import NotFoundFlag


class Dispatcher(Subject, Router):

    def __init__(self):
        super().__init__()
        self._allowed_args_for_handler = {
            'max_api': None,
            'update': None,
        }
        self.__logger = logging.getLogger('MaxDispatcher')


    async def notify(self, update: Update):
        if not update:
            return
        for handler in self._handlers:
            if await handler.update(update):
                args = [self._allowed_args_for_handler[arg] for arg in handler.args if arg in self._allowed_args_for_handler]
                await handler.function(*args)
                break

    async def _check_update(self, max_api: MaxApi):
        if not max_api.max_client._wait_recv:
            update = await max_api.max_client.wait_recv(return_updates=True)
            if not update:
                return NotFoundFlag()
            self.__logger.debug(f'Dispatcher update: %s', update)
            if update[0]['opcode'] == Opcode.PUSH_NOTIFICATION.value:
                self.__logger.debug('PUSH_NOTIFICATION')
                return Update(update[0]['payload'])
            self.__logger.debug('Dispatcher update skipped: %s', update)
        return NotFoundFlag()

    async def start_polling(self, max_api: MaxApi):
        max_api.max_client.update_fallback = self.notify
        self._allowed_args_for_handler['max_api'] = max_api
        while True:
            if max_api.max_client:
                update = await self._check_update(max_api)
                self._allowed_args_for_handler['update'] = update
                await self.notify(update)


    def include_router(self, router: Router):
        self._handlers += router._handlers


    def include_routers(self, routers: Iterable[Router]):
        for router in routers:
            self.include_router(router)

