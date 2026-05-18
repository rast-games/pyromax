from __future__ import annotations
import asyncio
from asyncio import CancelledError, Event, Task, Future
from collections.abc import Iterable
from typing import Any, Protocol, Awaitable, TYPE_CHECKING, TypeVar, Generic, Literal, cast

from ..utils import Correlator
from ..exceptions import AlreadyCancelledError
if TYPE_CHECKING:
    from ..protocol import Request, Response
    response = TypeVar('response', bound=Response)
    request = TypeVar('request', bound=Request[Any])
else:
    request = TypeVar('request')
    response = TypeVar('response')


class EventRouter(Generic[request, response]):
    """Event vs Response"""

    def __init__(self) -> None:
        self.correlator = Correlator()
        self.__pending: dict[tuple[request, int], Future[Any]] = {}
        # self.__updates: list[response] = []
        self.__updates: asyncio.Queue[Any] = asyncio.Queue()
        # self.__have_updates: Event = Event()

        self.__cancelled: bool = False

        self.__pop_updates_calls: list[Task[Any]] = []


    def _create_awaitable(self) -> Future[Any]:
        return asyncio.get_running_loop().create_future()


    async def add_to_updates(self, resp: response) -> None:
        # self.__updates.append(resp)
        await self.__updates.put(resp)


    def create_record(self, req: request, gen: int) -> Future[response]:
        """Create a record for the given request

        Raises
        -------
            AlreadyCancelledError
        """
        if self.__cancelled:
            raise AlreadyCancelledError('already canceled')

        awaitable = self._create_awaitable()

        key = (req, gen)

        self.__pending[key] = awaitable

        return awaitable


    async def resolve_response(self, resp: response, gen: int) -> bool:
        key = self.this_response_is_expecting(resp, gen)
        if key is not False:

            awaitable = self.__pending.pop(cast(tuple[request, int], key), None)

            if awaitable is None:
                return False
            if not awaitable.done():
                try:
                    awaitable.set_result(resp)
                    return True
                except asyncio.InvalidStateError:
                    return False
            return False
        await self.add_to_updates(resp)
        return False


    def cancel_request(self, req: request, gen: int) -> None:
        self.__pending.pop((req, gen), None)

    async def cancel_all(self) -> None:
        self.__cancelled = True
        pending_values: Iterable[Future[Any]] = self.__pending.values()
        for future_like in tuple(pending_values):
            future_like.cancel()
        try:
            await asyncio.gather(*tuple(self.__pending.values()), return_exceptions=True)
        except CancelledError:
            pass
        self.__pending.clear()

        for pop_updates_task in self.__pop_updates_calls:
            pop_updates_task.cancel()

        try:
            await asyncio.gather(*tuple(self.__pop_updates_calls), return_exceptions=True)
        except CancelledError:
            pass
        self.__pop_updates_calls.clear()


    def this_response_is_expecting(self, entry: response, entry_gen: int) -> tuple[request, int] | Literal[False]:
        for key in tuple(self.__pending):
            req, gen = key
            if req.is_my_response(entry) and gen == entry_gen:
                return key
        return False


    async def _pop_all_updates(self) -> list[response]:
        updates = [await self.__updates.get()]
        while True:
            try:
                update = self.__updates.get_nowait()
                updates.append(update)
            except asyncio.QueueEmpty:
                break
        return updates

    async def pop_all_updates(self) -> list[response]:
        """
        Get updates from event router

        Raises
        ------
            AlreadyCancelledError
        """
        pop_updates_task = asyncio.create_task(self._pop_all_updates())
        self.__pop_updates_calls.append(pop_updates_task)
        try:
            return await pop_updates_task
        except asyncio.CancelledError:
            raise AlreadyCancelledError('pop_all_updates cancelled')
        finally:
            if pop_updates_task in self.__pop_updates_calls:
                self.__pop_updates_calls.remove(pop_updates_task)
