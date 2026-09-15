from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import cast, AsyncGenerator, Any, TYPE_CHECKING, TypeVar

from .Router import Router
from .event import (
    UpdateMaxEventObserver,
    UNHANDLED,
    Update,
    UNKNOWN_UPDATE,
    skip,
    MaxObject,
    ResolvedUpdate,
)
from ..fsm.storage.memory import MemoryStorage, DisabledEventIsolation
from ..fsm.middleware import FSMContextMiddleware
from ..fsm.storage.base import BaseEventIsolation, BaseStorage
from ..fsm.strategy import FSMStrategy


from ..models import BaseMaxObject, DataDict, MapperUpdateTranslator
from ..protocol import Response
from .middlewares.error import ErrorsMiddleware
from .middlewares.user_context import UserContextMiddleware

if TYPE_CHECKING:
    from ..core.client import MaxApi


# class DataDict(dict):
#     """Just helper class for data in notify method"""


class Dispatcher(Router):
    """Top-level router that starts update polling.

    Dispatcher extends Router and is intended to be the root object
    that receives updates from MaxApi and dispatches them to handlers.
    """

    def __init__(
        self,
        *,
        storage: BaseStorage | None = None,
        fsm_strategy: FSMStrategy = FSMStrategy.USER_IN_CHAT,
        events_isolation: BaseEventIsolation | None = None,
        disable_fsm: bool = False,
        name: str | None = None,
        concurrent_task_dispatch: bool = False,
        concurrent_task_count: int = 100,
        **kwargs: Any,
    ) -> None:
        """Initialize the dispatcher.

        :param storage: BaseStorage instance to process.
        :type storage: BaseStorage | None
        :param fsm_strategy: FSMStrategy instance to process.
        :type fsm_strategy: FSMStrategy
        :param events_isolation: BaseEventIsolation instance to process.
        :type events_isolation: BaseEventIsolation | None
        :param disable_fsm: The disable fsm value.
        :type disable_fsm: bool
        :param name: The name value.
        :type name: str | None
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        """
        super().__init__(name=name)

        self._concurrent_task_dispatch = concurrent_task_dispatch
        self._concurrent_task_count = concurrent_task_count

        self.update = UpdateMaxEventObserver(
            router=self, event_name="UPDATE", type_of_update=MaxObject
        )

        async def notify_wrapper(
            resolved_update: ResolvedUpdate, data: DataDict
        ) -> Any:
            """Notify wrapper.

            :param resolved_update: ResolvedUpdate instance to process.
            :type resolved_update: ResolvedUpdate
            :param data: Contextual data passed through the processing pipeline.
            :type data: DataDict
            :returns: The value returned by the wrapped callable or backend.
            :rtype: Any
            """
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

        self.update.outer_middleware(ErrorsMiddleware(self))

        self.update.outer_middleware(UserContextMiddleware())

        self.fsm = FSMContextMiddleware(
            storage=storage or MemoryStorage(),
            strategy=fsm_strategy,
            events_isolation=events_isolation or DisabledEventIsolation(),
        )

        if not disable_fsm:
            self.update.outer_middleware(self.fsm)

        self.__logger = logging.getLogger("MaxDispatcher")

    def _process_update_with_semaphore(
        self,
        update: Update,
        data: dict[Any, Any],
        semaphore: asyncio.Semaphore,
        semaphore_calls: set[asyncio.Task[None]],
    ) -> None:
        async def semaphore_wrapper(
            update: Update,
            data: dict[Any, Any],
            semaphore: asyncio.Semaphore,
        ) -> None:
            async with semaphore:
                await self._process_update(update, data)

        task = asyncio.create_task(semaphore_wrapper(update, data, semaphore))
        semaphore_calls.add(task)

        task.add_done_callback(semaphore_calls.discard)

    async def _process_update(self, update: Update, data: dict[Any, Any]) -> None:
        update_observer = self.update

        response = await update_observer.wrap_outer_middleware(
            update_observer.update, update, data=data
        )

        handled = response is not UNHANDLED and response is not UNKNOWN_UPDATE
        self.__logger.debug(
            f'update %s was{"" if handled else "n`t"} handled: %s',
            update,
            handled,
        )

    async def start_polling(self, max_api: MaxApi) -> None:
        """Start reading updates and dispatch them to handlers.

        :param max_api: Initialized MaxApi instance.
        :type max_api: MaxApi
        """
        semaphore = asyncio.Semaphore(self._concurrent_task_count)
        semaphore_calls: set[asyncio.Task[None]] = set()

        context = {"max_api": max_api}

        update_translator, updates = max_api.listen_updates(context=context)
        try:
            async for update in updates:

                self.__logger.debug("Received update: %s", update)

                resolved_update = update_translator(update)

                data: dict[type | TypeVar, Any] = {
                    type(max_api): max_api,
                    Update: update,
                    ResolvedUpdate: resolved_update,
                }

                data.update(max_api.workflow_data)

                data[DataDict] = data
                if self._concurrent_task_dispatch:
                    self._process_update_with_semaphore(
                        update,
                        data,
                        semaphore,
                        semaphore_calls,
                    )
                else:
                    await self._process_update(update, data)
        finally:
            for task in semaphore_calls:
                with suppress(asyncio.CancelledError):
                    task.cancel()
                    await task
            await self.fsm.close()
            await max_api.stop()
