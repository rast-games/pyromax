from __future__ import annotations
import asyncio
from asyncio import Task, Future
from collections.abc import Iterable
from contextlib import suppress
from typing import (
    Any,
    TYPE_CHECKING,
    TypeVar,
    Generic,
    Literal,
    cast,
)

from ..utils import Correlator
from ..exceptions import AlreadyCancelledError, RoutingError, RequestWasCancelledError

if TYPE_CHECKING:
    from ..protocol import Request, Response

    response = TypeVar("response", bound=Response)
    request = TypeVar("request", bound=Request[Any])
else:
    request = TypeVar("request")
    response = TypeVar("response")


class EventRouter(Generic[request, response]):
    """Event vs Response"""

    def __init__(self, reset_lim: float | int) -> None:
        """Initialize the event router."""
        self.correlator = Correlator(reset_lim=reset_lim)
        self.__pending: dict[request, Future[Any]] = {}
        # self.__updates: list[response] = []
        self.__updates: asyncio.Queue[Any] = asyncio.Queue()
        # self.__have_updates: Event = Event()

        self.__cancelled: bool = False
        self._cancel_lock = asyncio.Lock()

        self.__pop_updates_calls: list[Task[Any]] = []

    def _create_awaitable(self) -> Future[Any]:
        """Create awaitable.

        :returns: The resulting Future[Any] value.
        :rtype: Future[Any]
        """
        return asyncio.get_running_loop().create_future()

    async def add_to_updates(self, resp: response) -> None:
        # self.__updates.append(resp)
        """Add to updates.

        :param resp: response instance to process.
        :type resp: response
        """
        await self.__updates.put(resp)

    def create_record(self, req: request) -> Future[response]:
        """Create a record for the given request

        :raises AlreadyCancelledError: If try create record in cancelled event router.

        :param req: request instance to process.
        :type req: request
        :returns: The resulting Future[response] value.
        :rtype: Future[response]
        """
        if self.__cancelled:
            raise AlreadyCancelledError("already canceled")

        if req in self.__pending:
            raise RoutingError("Request already registered")

        def on_done(done: Future[response]) -> None:
            if not done.cancelled():
                return

            if self.__pending.get(req) is done:
                self.__pending.pop(req, None)

        awaitable = self._create_awaitable()

        awaitable.add_done_callback(on_done)

        self.__pending[req] = awaitable

        return awaitable

    async def resolve_response(self, resp: response) -> bool:
        """Resolve response.

        :param resp: response instance to process.
        :type resp: response
        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        """
        if resp.is_update():
            await self.add_to_updates(resp)
            return False

        key = self.this_response_is_expecting(resp)

        if key is False:
            return False

        awaitable = self.__pending.pop(cast(request, key), None)  # type: ignore[redundant-cast]

        if awaitable is None:
            return False
        if not awaitable.done():
            try:
                awaitable.set_result(resp)
                return True
            except asyncio.InvalidStateError:
                return False
        return False

    async def cancel_request(self, req: request) -> None:
        """Cancel request.

        :param req: request instance to process.
        :type req: request
        """
        async with self._cancel_lock:
            awaitable = self.__pending.pop(req, None)
            if awaitable is None:
                return None
            try:
                awaitable.cancel()
                await awaitable
            except asyncio.CancelledError:
                task = asyncio.current_task()

                if task is not None and task.cancelling():
                    raise
            except asyncio.InvalidStateError:
                pass

    async def cancel_all(
        self,
        pending_exc: Exception | None = None,
        # update_calls_exc: Exception | None = None,
    ) -> None:
        """Cancel all."""
        async with self._cancel_lock:
            self.__cancelled = True
            pending_values: Iterable[Future[Any]] = self.__pending.values()
            if pending_exc is None:
                for future_like in tuple(pending_values):
                    with suppress(asyncio.InvalidStateError):
                        future_like.set_exception(
                            RequestWasCancelledError("Cancelled from cancel_all")
                        )
            else:
                for future_like in tuple(pending_values):
                    with suppress(asyncio.InvalidStateError):
                        future_like.set_exception(pending_exc)

            with suppress(asyncio.CancelledError, asyncio.InvalidStateError, Exception):
                await asyncio.gather(
                    *tuple(self.__pending.values()), return_exceptions=True
                )

            self.__pending.clear()

            # if update_calls_exc is None:
            for pop_updates_task in self.__pop_updates_calls:
                with suppress(asyncio.CancelledError, asyncio.InvalidStateError):
                    pop_updates_task.cancel()
            # else:
            #     for pop_updates_task in self.__pop_updates_calls:
            #         with suppress(asyncio.InvalidStateError):
            #             pop_updates_task.set_exception(update_calls_exc)

            with suppress(asyncio.CancelledError, Exception):
                await asyncio.gather(
                    *tuple(self.__pop_updates_calls), return_exceptions=True
                )

            self.__pop_updates_calls.clear()

    def this_response_is_expecting(self, entry: response) -> request | Literal[False]:
        """This response is expecting.

        :param entry: response instance to process.
        :type entry: response
        :returns: The resulting tuple[request, int] | Literal[False] value.
        :rtype: tuple[request, int] | Literal[False]
        """
        for key in tuple(self.__pending):
            req = key
            if req.is_my_response(entry):
                return key
        return False

    async def _pop_all_updates(self) -> list[response]:
        """Remove and return all updates.

        :returns: The resulting collection.
        :rtype: list[response]
        """
        updates = [await self.__updates.get()]
        while True:
            try:
                update = self.__updates.get_nowait()
                updates.append(update)
            except asyncio.QueueEmpty:
                break
        return updates

    async def pop_all_updates(self) -> list[response]:
        """Get updates from event router

        :raises AlreadyCancelledError: If the pop_all_updates was canceled while wait it.
        :raises RoutingError: if the pop_all_updates was canceled while wait it, but EventRouter not marked as canceled.

        :returns: The resulting collection.
        :rtype: list[response]
        """
        if self.__cancelled:
            raise AlreadyCancelledError("pop_all_updates cancelled")

        pop_updates_task = asyncio.create_task(self._pop_all_updates())
        self.__pop_updates_calls.append(pop_updates_task)
        try:
            return await pop_updates_task
        except asyncio.CancelledError:
            current_task = asyncio.current_task()
            if current_task is not None and current_task.cancelling():
                # Support for graceful shutdown, since the handled CancelledError error can be generated by the library
                # or created by the asyncio Runner.
                #
                # The asyncio.current_task().cancelling() check lets you know whether pop_all_updates itself, and
                # not _pop_all_updates, is being canceled. If it's True, this means pop_all_updates itself is being
                # canceled. Therefore, since the library itself doesn't cancel pop_all_updates anywhere, it's assumed
                # that the Runner is doing this.
                raise
            if self.__cancelled:
                raise AlreadyCancelledError("pop_all_updates cancelled")
            else:
                raise RoutingError(
                    "pop_all_updates cancelled, but EventRouter not marked as cancelled"
                )
        finally:
            if pop_updates_task in self.__pop_updates_calls:
                self.__pop_updates_calls.remove(pop_updates_task)
