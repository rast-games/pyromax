from __future__ import annotations

import abc
import asyncio
import logging
from collections.abc import Coroutine, Generator, Callable
from contextlib import suppress
from enum import Enum
from typing import TYPE_CHECKING, Any

from ....exceptions import (
    BackoffError,
    CircuitBreakerOpenError,
    MapperApiError,
    MapperCloseError,
    MapperConnectError,
    MapperLifecycleError,
    MapperRestartCycleError,
    NeedReloginMapperError,
    RestartMapperError,
    StopLifecycleError,
    UnsupportedClientVersionMapperError,
)
from ....utils import Backoff
from .constants import DEFAULT_BACKOFF_CONFIG

if TYPE_CHECKING:
    from .Mapper import Mapper


class _LifecycleStates(Enum):
    CONNECTED = 1
    CONNECTING = 2
    DISCONNECTED = 3
    DISCONNECTING = 4


class BaseAuthContainer(abc.ABC):

    @abc.abstractmethod
    async def authorize(self) -> None: ...


class DefaultAuthContainer(BaseAuthContainer):

    def __init__(self, mapper: Mapper) -> None:
        self._mapper = mapper

    async def authorize(self) -> None:
        if not self._mapper.logged:
            await self._mapper.login()
        else:
            await self._mapper._send_user_agent()

        await self._mapper._send_auth_token()
        telemetry = self._mapper._telemetry
        if telemetry is not None:
            await telemetry.start()


class OnlyUserAgentAuthContainer(BaseAuthContainer):
    def __init__(self, mapper: Mapper) -> None:
        self._mapper = mapper

    async def authorize(self) -> None:
        await self._mapper._send_user_agent()


class LifecycleFailure:
    def __init__(self, exception: Exception, source: str, generation: int):
        """Initialize the lifecycle failure.

        :param exception: Exception instance to process.
        :type exception: Exception
        :param source: The source value.
        :type source: str
        :param generation: The generation value.
        :type generation: int
        """
        self.exception = exception
        self.source = source
        self.generation: int = generation

    def __repr__(self) -> str:
        """Return the developer representation of the lifecycle failure.

        :returns: The resulting str value.
        :rtype: str
        """
        return f"exception: {self.exception}, source: {self.source}, generation: {self.generation}"


class LifecycleManager:

    def __init__(
        self,
        mapper: Mapper,
        connect_timeout: int | None = 15,
        auth_container: BaseAuthContainer | None = None,
    ) -> None:
        if auth_container is None:
            auth_container = DefaultAuthContainer(mapper)

        self.connect_timeout = connect_timeout
        self._mapper = mapper
        self._auth_container = auth_container

        self._logger = logging.getLogger("LifecycleManagerEnvelopeMapperV11")

        self._manage_lifecycle_task: asyncio.Task[Any] | None = None
        self._lifecycle_queue: asyncio.Queue[LifecycleFailure] = asyncio.Queue(
            maxsize=1
        )

        self._generation = 0
        self._state: _LifecycleStates = _LifecycleStates.DISCONNECTED
        self._running: bool = False
        self._ready = asyncio.Event()

    def make_error_reporter(self) -> Callable[[Exception, str], None]:
        generation = self.get_generation()

        def report(exception: Exception, source: str) -> None:
            if generation != self.get_generation():
                return

            self.notify_about_exception(
                exception,
                generation=generation,
                source=source,
            )

        return report

    async def start(self) -> None:
        """Idempotently start lifecycle management."""

        task = self._manage_lifecycle_task

        if task is not None and not task.done():
            return

        self._ready.clear()
        self._running = True
        self._manage_lifecycle_task = asyncio.create_task(self._manage_lifecycle())

    async def wait_until_connected(self) -> None:
        """Wait until the requested lifecycle mode is ready.

        Normal mode becomes ready after authorization.  Auth-flow mode becomes
        ready after the transport is connected and the user agent is sent.
        Lifecycle failures are propagated instead of leaving callers waiting
        forever on an event that can no longer be set.
        """
        task = self._manage_lifecycle_task
        if task is None:
            raise RuntimeError("Lifecycle manager is not started")

        ready_task = asyncio.create_task(self._ready.wait())
        try:
            done, _ = await asyncio.wait(
                (ready_task, task),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if task in done:
                await task
                if not self._ready.is_set():
                    raise MapperLifecycleError(
                        "Lifecycle stopped before the mapper became ready"
                    )
        finally:
            if not ready_task.done():
                ready_task.cancel()
                await asyncio.gather(ready_task, return_exceptions=True)

    async def request_reconnect(self, exception: Exception) -> None:
        """Request a reconnect and wait for the replacement connection."""
        if self._state is not _LifecycleStates.CONNECTED or not self._running:
            return

        self._ready.clear()
        self._mapper._authorized.clear()
        self._mapper._mapper_connected.clear()
        self._mapper._protocol_connected.clear()
        self.notify_about_exception(
            exception,
            generation=self.get_generation(),
            source="LifecycleManager.request_reconnect",
        )
        await self.wait_until_connected()

    async def stop(self) -> None:
        """Idempotently stop lifecycle management and close the mapper."""
        self._running = False
        self._ready.clear()
        task = self._manage_lifecycle_task
        self._manage_lifecycle_task = None
        try:
            if task is not None and task is not asyncio.current_task():
                with suppress(asyncio.CancelledError):
                    task.cancel()
                    await task
        finally:
            await self._mapper.close(StopLifecycleError("Lifecycle was stopped"))

    async def _connect(self) -> None:
        self._next_generation()

        await self._close()

        try:
            self._state = _LifecycleStates.CONNECTING
            if self.connect_timeout is None:
                await self._mapper.connect()
            else:
                await asyncio.wait_for(
                    self._mapper.connect(), timeout=self.connect_timeout
                )
            self._state = _LifecycleStates.CONNECTED
        except TimeoutError as e:
            self._state = _LifecycleStates.DISCONNECTED
            raise MapperConnectError("Mapper connection timed out") from e
        except MapperConnectError as e:
            self._logger.error(e)
            self._state = _LifecycleStates.DISCONNECTED
            raise

    async def _close(self) -> None:
        try:
            self._state = _LifecycleStates.DISCONNECTING
            await self._mapper.close()
            self._state = _LifecycleStates.DISCONNECTED
        except MapperCloseError as e:
            self._logger.error(e)
            self._state = _LifecycleStates.DISCONNECTED
            raise

    async def _asleep_backoff(self, backoff: Backoff) -> None:
        try:
            await backoff.asleep()
        except BackoffError:
            self._logger.warning("Backoff get max of offset")
            backoff.reset()

    async def _handle_disconnect(self, exception: Exception) -> None:
        """Close the failed connection, notify handlers, and wait to reconnect."""
        self._ready.clear()
        try:
            self._state = _LifecycleStates.DISCONNECTING
            with suppress(MapperCloseError):
                await self._mapper.close(exception)
        finally:
            self._state = _LifecycleStates.DISCONNECTED

        if not await self._mapper._handle_disconnect(exception):
            raise exception

    async def _wait_for_circuit_breaker(
        self, exception: CircuitBreakerOpenError
    ) -> None:
        """Wait for an open mapper circuit without restarting the lifecycle."""
        breaker = None
        if exception.circuit == "transport":
            breaker = self._mapper.transport_circuit_breaker
        elif exception.circuit == "api":
            breaker = self._mapper.api_circuit_breaker

        self._logger.warning(
            "Mapper %s circuit is open; lifecycle authorization will wait",
            exception.circuit or "unknown",
        )
        if breaker is not None:
            await breaker.wait_until_available()
            return
        await asyncio.sleep(exception.retry_after)

    async def _observe_task(
        self,
        coro: Coroutine[Any, Any, None],
        observer: Coroutine[Any, Any, None] | None = None,
    ) -> None:
        if observer is None:
            observer = self._observe_error()

        try:
            async with asyncio.TaskGroup() as tg:
                error_getter = tg.create_task(observer)
                main_task = tg.create_task(coro)

                await main_task

                error_getter.cancel()

        except BaseExceptionGroup as group:
            exceptions = tuple(self._flatten_exception_group(group))
            if not exceptions:
                raise

            priority = (
                UnsupportedClientVersionMapperError,
                NeedReloginMapperError,
                CircuitBreakerOpenError,
                MapperApiError,
                MapperCloseError,
                MapperConnectError,
                MapperRestartCycleError,
                RestartMapperError,
            )
            for error_type in priority:
                for error in exceptions:
                    if isinstance(error, error_type):
                        raise error

            original_error = exceptions[0]
            if isinstance(original_error, asyncio.CancelledError):
                raise original_error
            if isinstance(original_error, Exception):
                raise MapperRestartCycleError("Observe task failed") from original_error
            raise original_error

    async def _observe_error(self, generation: int | None = None) -> None:
        """Observe auth error.

        :raises MapperLifecycleError: If _observe_error.
        """
        if generation is None:
            generation = self.get_generation()

        while True:
            error_state = await self._lifecycle_queue.get()

            if error_state.generation == generation:
                raise error_state.exception

    async def _observe_auth_error(self, generation: int | None = None) -> None:
        """Backward-compatible authorization error observer."""
        await self._observe_error(generation)

    async def _authorize(self) -> None:
        await self._connect()

        await self._auth_container.authorize()

    async def _manage_lifecycle(self) -> None:
        manage_lifecycle_backoff = Backoff(DEFAULT_BACKOFF_CONFIG)
        try:
            while self._running:
                if self._state in (
                    _LifecycleStates.DISCONNECTED,
                    _LifecycleStates.DISCONNECTING,
                ):
                    while True:
                        try:
                            generation = self.get_next_generation()
                            await self._observe_task(
                                coro=self._authorize(),
                                observer=self._observe_auth_error(generation),
                            )
                            manage_lifecycle_backoff.reset()
                            self._ready.set()
                            break
                        except NeedReloginMapperError as e:
                            if not self._mapper.extra_config.relogin:
                                await self._handle_disconnect(e)
                                raise
                            await self._handle_disconnect(e)
                            continue
                        except MapperCloseError as e:
                            self._logger.exception("Error while closing in lifecycle")
                            await self._handle_disconnect(e)

                            await self._asleep_backoff(manage_lifecycle_backoff)

                            continue

                        except MapperConnectError as e:
                            self._logger.exception(
                                "Error while connecting in lifecycle"
                            )
                            await self._handle_disconnect(e)

                            await self._asleep_backoff(manage_lifecycle_backoff)
                            continue

                        except MapperApiError as e:
                            self._logger.exception("API error occurred in lifecycle")
                            await self._mapper._propagate_api_error(e)

                            await self._handle_disconnect(e)

                            await self._asleep_backoff(manage_lifecycle_backoff)
                            continue

                        except CircuitBreakerOpenError as e:
                            await self._handle_disconnect(e)

                            await self._wait_for_circuit_breaker(e)

                            continue

                        except MapperRestartCycleError as e:
                            await self._handle_disconnect(e)

                            await self._asleep_backoff(manage_lifecycle_backoff)

                            continue
                        except RestartMapperError as e:
                            await self._handle_disconnect(e)
                            await self._asleep_backoff(manage_lifecycle_backoff)
                            continue

                await self._mapper._mapper_connected.wait()
                current_error_state = await self._lifecycle_queue.get()
                self._logger.warning("Catch exception")
                self._logger.debug("Current generation=%s", self.get_generation())
                msg = (
                    f"error: {current_error_state.exception}, "
                    f"source: {current_error_state.source}, "
                    f"gen: {current_error_state.generation}, "
                )
                self._logger.error(msg)
                if current_error_state.generation != self.get_generation():
                    continue

                await self._handle_disconnect(current_error_state.exception)
        except asyncio.CancelledError:
            raise
        except Exception:
            self._logger.exception("Lifecycle stopped with an error")
            self._running = False
            self._ready.clear()
            if not self._mapper.extra_config.reconnect:
                self._mapper.max_api.request_shutdown()
            raise
        finally:
            if self._manage_lifecycle_task is asyncio.current_task():
                self._manage_lifecycle_task = None

    def notify_about_exception(
        self, exception: Exception, generation: int, source: str
    ) -> None:
        """Notify about exception.

        :param exception: Exception instance to process.
        :type exception: Exception
        :param generation: The generation value.
        :type generation: int
        :param source: The source value.
        :type source: str
        """
        try:
            while True:
                try:
                    self._lifecycle_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

            self._lifecycle_queue.put_nowait(
                LifecycleFailure(
                    generation=generation,
                    exception=exception,
                    source=source,
                )
            )
        except asyncio.QueueFull:
            self._logger.debug(
                "Failure already queued, dropping duplicate from %s",
                source,
            )
            self._logger.debug(
                LifecycleFailure(
                    generation=generation,
                    exception=exception,
                    source=source,
                )
            )

    def get_generation(self) -> int:
        """Retrieve generation.

        :returns: The resulting int value.
        :rtype: int
        """
        return self._generation

    def get_next_generation(self) -> int:
        """Retrieve next generation.

        :returns: The resulting int value.
        :rtype: int
        """
        return self.get_generation() + 1

    def _next_generation(self) -> int:
        """Next generation.

        :returns: The resulting int value.
        :rtype: int
        """
        self._generation += 1
        return self._generation

    @staticmethod
    def _flatten_exception_group(
        exception: BaseException,
    ) -> Generator[BaseException, None, None]:
        """Yield leaf exceptions from a possibly nested exception group."""
        if isinstance(exception, BaseExceptionGroup):
            for nested_exception in exception.exceptions:
                yield from LifecycleManager._flatten_exception_group(nested_exception)
            return
        yield exception
