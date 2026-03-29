import asyncio
from asyncio import CancelledError, Event, Task
from typing import Any, Protocol, Awaitable

from src.pyromax.protocol.bases.request_response import Request, Response
from src.pyromax.utils import Correlator


class FutureLikeObject(Protocol, Awaitable):

    def set_result(self, result: Any) -> None: pass


    def result(self) -> Any: pass


    def cancel(self) -> None: pass


class EventRouter:
    """Event vs Response"""

    def __init__(self):
        self.correlator = Correlator()
        self.__pending: dict[Request, FutureLikeObject] = {}
        self.__updates: list[Response] = []
        self.__have_updates: Event = Event()

        self.__cancelled = False

        self.__pop_updates_calls: list[Task] = []


    def _create_awaitable(self) -> FutureLikeObject:
        return asyncio.get_running_loop().create_future()


    def add_to_updates(self, response):
        self.__updates.append(response)


    async def create_record(self, request: Request) -> FutureLikeObject:
        awaitable = self._create_awaitable()

        if self.__cancelled:
            raise CancelledError('already canceled')

        self.__pending[request] = awaitable

        return awaitable



    async def resolve_response(self, response: Response) -> bool:
        request = self.this_response_is_expecting(response)
        if request:
            awaitable = self.__pending.pop(request)
            awaitable.set_result(response)
            return True

        self.add_to_updates(response)
        self.__have_updates.set()
        return False


    def cancel_all(self):
        for future_like in self.__pending.values():
            future_like.cancel()

        for pop_updates_task in self.__pop_updates_calls:
            pop_updates_task.cancel()

        self.__cancelled = True

    def this_response_is_expecting(self, entry: Response) -> Request | bool:
        for request in self.__pending.copy():
            if request.is_my_response(entry):
                return request
        return False


    async def _pop_all_updates(self) -> list[Response]:
        await self.__have_updates.wait()
        updates = self.__updates
        self.__updates = []
        self.__have_updates.clear()
        return updates


    async def pop_all_updates(self):
        pop_updates_task = asyncio.create_task(self._pop_all_updates())
        self.__pop_updates_calls.append(pop_updates_task)
        return await pop_updates_task


    def __del__(self):
        for pop_updates_task in self.__pop_updates_calls:
            pop_updates_task.cancel()