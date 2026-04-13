from __future__ import annotations
import asyncio
from asyncio import CancelledError, Event, Task, Future
from typing import Any, Protocol, Awaitable, TYPE_CHECKING, TypeVar, Generic, Literal

from ..utils import Correlator
if TYPE_CHECKING:
    from ..protocol import Request, Response



    response = TypeVar('response', bound=Response)
    request = TypeVar('request', bound=Request[Any])
else:
    request = TypeVar('request')
    response = TypeVar('response')

# class FutureLikeObject(Protocol, Awaitable[Response]):
#
#     def set_result(self, result: Any) -> None: pass
#
#
#     def result(self) -> Any: pass
#
#
#     def cancel(self) -> None: pass



class EventRouter(Generic[request, response]):
    """Event vs Response"""

    def __init__(self) -> None:
        self.correlator = Correlator()
        self.__pending: dict[request, Future[Any]] = {}
        self.__updates: list[response] = []
        self.__have_updates: Event = Event()

        self.__cancelled: bool = False

        self.__pop_updates_calls: list[Task[Any]] = []


    def _create_awaitable(self) -> Future[Any]:
        return asyncio.get_running_loop().create_future()


    def add_to_updates(self, resp: response) -> None:
        self.__updates.append(resp)


    def create_record(self, req: request) -> Future[response]:
        awaitable = self._create_awaitable()

        if self.__cancelled:
            raise CancelledError('already canceled')

        self.__pending[req] = awaitable

        return awaitable



    def resolve_response(self, resp: response) -> bool:
        req = self.this_response_is_expecting(resp)
        if req is not False:
            awaitable = self.__pending.pop(req)
            awaitable.set_result(resp)
            return True

        self.add_to_updates(resp)
        self.__have_updates.set()
        return False


    def cancel_all(self) -> None:
        for future_like in self.__pending.values():
            future_like.cancel()

        for pop_updates_task in self.__pop_updates_calls:
            pop_updates_task.cancel()

        self.__cancelled = True

    def this_response_is_expecting(self, entry: response) -> request | Literal[False]:
        for req in self.__pending.copy():
            if req.is_my_response(entry):
                return req
        return False


    async def _pop_all_updates(self) -> list[response]:
        await self.__have_updates.wait()
        updates = self.__updates
        self.__updates = []
        self.__have_updates.clear()
        return updates


    async def pop_all_updates(self) -> list[response]:
        pop_updates_task = asyncio.create_task(self._pop_all_updates())
        self.__pop_updates_calls.append(pop_updates_task)
        return await pop_updates_task


    def __del__(self) -> None:
        for pop_updates_task in self.__pop_updates_calls:
            pop_updates_task.cancel()