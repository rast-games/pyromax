import logging
from typing import cast, AsyncGenerator

from .Router import Router
from ..core.client import MaxApi


class Dispatcher(Router):
    def __init__(self):
        super().__init__()

        self.__logger = logging.getLogger('MaxDispatcher')


    async def start_polling(self, max_api: MaxApi):

        context = {
            'max_api': max_api
        }

        async for update in cast(AsyncGenerator, max_api.mapper.listen_updates(context=context)):

            self.__logger.debug('Received update: %s', update)

            data = {
                MaxApi: max_api,
                type(update): update,
            }


            handled = await self.notify(
                update=update,
                data=data,
            )
            self.__logger.debug(f'update %s was{"" if handled else "n`t"} handled: %s', update, handled)


