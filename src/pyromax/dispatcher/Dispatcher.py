from __future__ import annotations
import logging
from typing import cast, AsyncGenerator, Any, TYPE_CHECKING

from .Router import Router
from .event import UpdateMaxEventObserver, UNHANDLED, Update, UNKNOWN_UPDATE, skip, MaxObject

from ..models import BaseMaxObject, DataDict, MapperUpdateTranslator
from ..protocol import Response
from .middlewares.error import ErrorsMiddleware


if TYPE_CHECKING:
    from ..core.client import MaxApi


# class DataDict(dict):
#     """Just helper class for data in notify method"""


class Dispatcher(Router):
    """Top-level router that starts update polling.

    Dispatcher extends Router and is intended to be the root object
    that receives updates from MaxApi and dispatches them to handlers.
    """
    def __init__(self) -> None:
        super().__init__()

        self.update = UpdateMaxEventObserver(
            router=self,
            event_name="UPDATE",
            type_of_update=MaxObject
        )

        async def notify_wrapper(update: Update, data: DataDict) -> Any:
            # try:
            mapper_update_translator = data.pop(MapperUpdateTranslator)
            # except KeyError:
            #     skip()
            resolved_update = mapper_update_translator(update)
            data.update(
                {
                    type(resolved_update): resolved_update,
                }
            )
            result = await self.notify(resolved_update, data)
            if result is UNKNOWN_UPDATE:
                skip()
            return result

        self.update.register(notify_wrapper)

        self.update.outer_middleware(
            ErrorsMiddleware(self)
        )

        self.__logger = logging.getLogger('MaxDispatcher')



    async def start_polling(self, max_api: MaxApi) -> None:
        """Start reading updates and dispatch them to handlers.

        Parameters
        ----------
        max_api
            Initialized MaxApi instance.
        """

        context = {
            'max_api': max_api
        }

        update_translator, updates = max_api.listen_updates(context=context)
        # async for update in cast(AsyncGenerator[Response | BaseMaxObject, None], max_api.listen_updates(context=context)):
        async for update in updates:

            self.__logger.debug('Received update: %s', update)

            data: dict[type, Any] = {
                type(max_api): max_api,
                Update: update
            }

            data.update(
                {
                    MapperUpdateTranslator: update_translator
                }
            )
            data.update(max_api.workflow_data)

            update_observer = self.update

            data[DataDict] = data

            response = await update_observer.wrap_outer_middleware(
                update_observer.update,
                update,
                data=data
            )

            handled = response is not UNHANDLED and response is not UNKNOWN_UPDATE

            self.__logger.debug(f'update %s was{"" if handled is not UNHANDLED else "n`t"} handled: %s', update, handled)


