from __future__ import annotations
import logging
from typing import cast, AsyncGenerator, Any, TYPE_CHECKING

from .Router import Router
from .event import Update

# from .. import BaseMaxObject, Response
from ..models import BaseMaxObject
from ..protocol import Response

if TYPE_CHECKING:
    from ..core.client import MaxApi


class Dispatcher(Router):
    def __init__(self) -> None:
        super().__init__()

        self.__logger = logging.getLogger('MaxDispatcher')


    async def start_polling(self, max_api: MaxApi) -> None:

        context = {
            'max_api': max_api
        }

        async for update in cast(AsyncGenerator[Response | BaseMaxObject, None], max_api.mapper.listen_updates(context=context)):

            self.__logger.debug('Received update: %s', update)

            data = {
                type(max_api): max_api,
                type(update): update,
            }


            handled = await self.notify(
                update=update,
                data=data,
            )
            self.__logger.debug(f'update %s was{"" if handled else "n`t"} handled: %s', update, handled)


