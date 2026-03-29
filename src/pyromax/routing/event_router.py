import asyncio
from asyncio import Future, CancelledError, Event, Task
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


    # def update(self, response: Response) -> None:
    #     # self.correlator
    #
    #
    #     if self.check_entry(invert_update):
    #         request = self.__pending.pop(invert_update)
    #         request.set_result(update)
    #
    #     else:
    #         self.add_to_responses(update)


        # if not self.check_entry(invert_update):
        #     print(f'Event:')
        #     from pprint import pprint
        #     pprint(update.model_dump())
        #     return True
        # else:
        #
        #
        # if not self.correlator.push(update, invert_update):
        #     print(f'Event:')
        #     from pprint import pprint
        #     pprint(update.model_dump())
        #     return False
        # return True



    def _create_awaitable(self) -> FutureLikeObject:
        return asyncio.get_running_loop().create_future()


    def add_to_updates(self, response):
        self.__updates.append(response)


    async def create_record(self, request: Request) -> FutureLikeObject:
        awaitable = self._create_awaitable()

        if self.__cancelled:
            raise CancelledError('already canceled')

        # for inx, response in enumerate(self.__updates):
        #     if request.is_my_response(response):
        #         responses = self.__updates
        #         response = responses.pop(inx)
        #         awaitable.set_result(response)
        #         return awaitable

        self.__pending[request] = awaitable

        return awaitable



    async def resolve_response(self, response: Response) -> bool:
        # if request in self.__pending:
        #     request = self.__pending.pop(request)
        #     request.set_result(response)
        #     print(f'Response: {response}')
        #     return True
        # return False

        request = self.this_response_is_expecting(response)

        from pprint import pprint

        if request:
            print('Response:')
            pprint(response)
            awaitable = self.__pending.pop(request)
            awaitable.set_result(response)
            return True

        self.add_to_updates(response)
        self.__have_updates.set()
        print('Event:')
        pprint(self.__updates)
        pprint(response)
        return False

        # for request in self.__pending.copy():
        #     if request.is_my_response(response):
        #         awaitable = self.__pending.pop(request)
        #         awaitable.set_result(response)
        #         return True
        # self.add_to_responses(response)
        #
        # return False

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
        # if entry in self.__pending:
        #     return True
        # return False


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

