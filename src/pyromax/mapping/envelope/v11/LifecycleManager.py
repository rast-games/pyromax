from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING, Any
import logging
from enum import Enum

from ....utils import Backoff
from .constants import DEFAULT_BACKOFF_CONFIG
from ....exceptions import RestartMapperError, AlreadyFailedError, BackoffError, MapperCancelledError

if TYPE_CHECKING:
    from .Mapper import Mapper


class _LifecycleStates(Enum):
    CONNECTED = 1
    CONNECTING = 2
    DISCONNECTED = 3
    DISCONNECTING = 4
    # ERROR = 5

class LifecycleFailure:
    def __init__(self, exception: Exception, source: str, generation: int):
        self.exception = exception
        self.source = source
        self.generation: int = generation


    def __repr__(self) -> str:
        return f'exception: {self.exception}, source: {self.source}, generation: {self.generation}'

class LifecycleManager:
    def __init__(self, mapper: Mapper, connect_timeout: int = 5):
        self.mapper = mapper
        self._logger = logging.getLogger('LifecycleManagerEnvelopeMapperV11')
        self._manage_lifecycle_task: asyncio.Task | None = None
        self.connect_timeout = connect_timeout
        # self._fallback_waiter_task: asyncio.Task | None = None
        # self._lifecycle_task_lock: asyncio.Lock = asyncio.Lock()
        # self._mapper_correctly_running: asyncio.Event = asyncio.Event()
        # self.__fallback_waiter_timeout = fallback_waiter_timeout
        # self._has_lifecycle_task: asyncio.Event = asyncio.Event()


        self._lifecycle_queue: asyncio.Queue[LifecycleFailure] = asyncio.Queue(maxsize=1)
        self._generation: int = 0
        self._generation_lock: asyncio.Lock = asyncio.Lock()
        self._state: _LifecycleStates = _LifecycleStates.DISCONNECTED


    def notify_about_exception(self, exception: Exception, generation: int, source: str) -> None:
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
                'failure already queued, dropping duplicate from %s',
                source,
            )
            self._logger.debug(LifecycleFailure(
                    generation=generation,
                    exception=exception,
                    source=source,
                ))

    def start(self, auth_params: dict[str, Any] | None = None, **kwargs) -> None:
        task = self._manage_lifecycle_task

        if task is not None and not task.done():
            return

        if auth_params is None:
            auth_params = {}

        self._manage_lifecycle_task = asyncio.create_task(
            self._manage_lifecycle(auth_params=auth_params, **kwargs)
        )


    async def _close(self):
        try:
            await self.mapper.close()
        except Exception:
            self._logger.exception('close failed')


    async def _connect(self, manage_lifecycle_backoff, auth_params: dict | None = None, **kwargs: dict[str, Any]) -> None:
        if auth_params is None:
            auth_params = {}
        await self.mapper.connect()
        if not self.mapper.logged or not self.mapper.token:
            await self.mapper.login(kwargs.get('url_callback'), login_backoff=manage_lifecycle_backoff)
            self.mapper.logged = True
        await self.mapper._auth(
            token=self.mapper.token,
            user_agent=self.mapper.user_agent,
            **auth_params
        )
        self.mapper._authorized.set()
        self._logger.debug('auth token sent')


    async def _establish_connection(self, manage_lifecycle_backoff, auth_params: dict[str, Any] | None = None, close_firstly: bool = True, **kwargs: dict[str, Any]):
        try:
            if close_firstly:
                self._state = _LifecycleStates.DISCONNECTING
                await self._close()
                self._state = _LifecycleStates.DISCONNECTED
            self._state = _LifecycleStates.CONNECTING
            await self._connect(manage_lifecycle_backoff=manage_lifecycle_backoff, auth_params=auth_params, kwargs=kwargs)
            await self._next_generation()
            self._state = _LifecycleStates.CONNECTED
        except Exception as e:
            try:
                self._state = _LifecycleStates.DISCONNECTING
                await self._close()
            finally:
                self._state = _LifecycleStates.DISCONNECTED

            self._logger.warning('connection failed', exc_info=True)
            raise
        except asyncio.CancelledError:
            try:
                self._state = _LifecycleStates.DISCONNECTING
                await self._close()
            finally:
                self._state = _LifecycleStates.DISCONNECTED

            self._logger.warning('connection cancelled')
            raise

    async def _manage_lifecycle(self, auth_params: dict[str, Any], **kwargs) -> None:
        manage_lifecycle_backoff = Backoff(DEFAULT_BACKOFF_CONFIG)
        while True:
            if self._state in (
                _LifecycleStates.DISCONNECTED,
                _LifecycleStates.DISCONNECTING
            ):
                try:
                    try:
                        await asyncio.wait_for(self._establish_connection(auth_params=auth_params,
                                                         manage_lifecycle_backoff=manage_lifecycle_backoff,
                                                         close_firstly=True,
                                                                          **kwargs),
                                               timeout=self.connect_timeout)
                        await manage_lifecycle_backoff.asleep()
                    except BackoffError:
                        self._logger.debug('timeout while waiting for lifecycle backoff')
                    manage_lifecycle_backoff.reset()
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    self._logger.exception('unexpected exception in _manage_lifecycle while establish_connection')
                    continue

            current_error_state = await self._lifecycle_queue.get()
            # self._lifecycle_queue.task_done()
            self._logger.warning('catch protocol failed')
            self._logger.error(
f'''
error: {current_error_state.exception}
source: {current_error_state.source},
gen: {current_error_state.generation},
'''
            )
            if current_error_state.generation != await self.get_generation():
                continue
            while True:
                try:
                    try:
                        await asyncio.wait_for(self._establish_connection(auth_params=auth_params, manage_lifecycle_backoff=manage_lifecycle_backoff, close_firstly=True, **kwargs), timeout=self.connect_timeout)
                        # await self._drain_failures()
                        break
                    except asyncio.TimeoutError:
                        self._logger.warning('timeout while waiting for connection after error')
                        await manage_lifecycle_backoff.asleep()
                    except Exception as e:
                        self._logger.exception('establish connection failed')
                        await manage_lifecycle_backoff.asleep()
                        continue
                except BackoffError:
                    self._logger.warning('backoff timeout while waiting for connection after error')
            manage_lifecycle_backoff.reset()


    async def get_generation(self) -> int:
        async with self._generation_lock:
            return self._generation


    async def get_next_generation(self) -> int:
        return await self.get_generation() + 1


    async def _next_generation(self) -> int:
        async with self._generation_lock:
            self._generation += 1
            return self._generation


    async def _drain_failures(self):
        while True:
            try:
                failure = self._lifecycle_queue.get_nowait()
                self._lifecycle_queue.task_done()

            except asyncio.QueueEmpty:
                return

            self._logger.debug(
                'dropping duplicated failure from %s',
                failure.source,
            )