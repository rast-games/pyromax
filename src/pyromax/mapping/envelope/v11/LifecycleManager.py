from __future__ import annotations
import asyncio
from asyncio import wait_for
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, Any, Coroutine, cast
import logging
from enum import Enum

from ....utils import Backoff
from .constants import DEFAULT_BACKOFF_CONFIG
from ....exceptions import RestartMapperError, AlreadyFailedError, BackoffError, MapperCancelledError, MapperLifecycleError

if TYPE_CHECKING:
    from .Mapper import Mapper


class _LifecycleStates(Enum):
    CONNECTED = 1
    CONNECTING = 2
    DISCONNECTED = 3
    DISCONNECTING = 4

class LifecycleFailure:
    def __init__(self, exception: Exception, source: str, generation: int):
        self.exception = exception
        self.source = source
        self.generation: int = generation


    def __repr__(self) -> str:
        return f'exception: {self.exception}, source: {self.source}, generation: {self.generation}'

class LifecycleManager:
    def __init__(self, mapper: Mapper, connect_timeout: int | None = 15):
        if connect_timeout is None:
            connect_timeout = 5
        self.mapper = mapper
        self._logger = logging.getLogger('LifecycleManagerEnvelopeMapperV11')
        self._manage_lifecycle_task: asyncio.Task[Any] | None = None
        self.connect_timeout = connect_timeout


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

    def start(self, auth_params: dict[str, Any] | None = None, **kwargs: Any) -> None:
        task = self._manage_lifecycle_task

        if task is not None and not task.done():
            return

        if auth_params is None:
            auth_params = {}

        self._manage_lifecycle_task = asyncio.create_task(
            self._manage_lifecycle(auth_params=auth_params, **kwargs)
        )


    async def _close(self) -> None:
        try:
            await self.mapper.close()
        except Exception:
            self._logger.exception('close failed')


    async def _connect(self, manage_lifecycle_backoff: Backoff, auth_params: dict[str, Any] | None = None, url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None, **kwargs: Any) -> None:
        if auth_params is None:
            auth_params = {}
        await self.mapper.connect()
        if not self.mapper.logged or not self.mapper.token:
            await self.mapper.login(url_callback=url_callback, login_backoff=manage_lifecycle_backoff)
            self.mapper.logged = True

        token = self.mapper.token
        user_agent = self.mapper.user_agent

        assert token is not None
        assert user_agent is not None

        await self.mapper._auth(
            token=token,
            user_agent=user_agent,
            **auth_params
        )
        self.mapper._authorized.set()
        self._logger.debug('auth token sent')


    async def _establish_connection(self, manage_lifecycle_backoff: Backoff, auth_params: dict[str, Any] | None = None, close_firstly: bool = True, **kwargs: Any) -> None:
        # from random import random
        #
        # rnd = random()
        # print(rnd)
        # if rnd > 0.5:
        #     print('sleeping')
        #     await asyncio.sleep(20)

        try:
            if close_firstly:
                self._state = _LifecycleStates.DISCONNECTING
                await self._close()
                self._state = _LifecycleStates.DISCONNECTED
            self._state = _LifecycleStates.CONNECTING
            await self._connect(manage_lifecycle_backoff=manage_lifecycle_backoff, auth_params=auth_params, **kwargs)
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

    async def _observe_auth_error(self) -> None:
        while True:
            gen = await self.get_next_generation()
            if not self.mapper._authorized.is_set():
                error_state = await self._lifecycle_queue.get()
            else:
                return
            if error_state and error_state.generation != gen:
                continue
            if not self.mapper._authorized.is_set():
                raise MapperLifecycleError('_observe_error')
            elif self.mapper._authorized.is_set():
                try:
                    self._lifecycle_queue.put_nowait(error_state)
                except asyncio.QueueFull:
                    pass


    async def _observe_task(
            self,
            observer_coroutine: Coroutine[Any, Any, None],
            first_observe_coroutine: Coroutine[Any, Any, Any],
            *other_coroutines: Coroutine[Any, Any, Any],
    ) -> None:
        try:
            all_tasks = [first_observe_coroutine, *other_coroutines]
            async with asyncio.TaskGroup() as tg:
                observe_task = tg.create_task(observer_coroutine)
                main_tasks = []
                for task in all_tasks:
                    main_tasks.append(tg.create_task(task))
                await asyncio.gather(*main_tasks)
                observe_task.cancel()


        except* Exception as eg:
            original_error = eg.exceptions[0] if eg.exceptions else eg
            self._logger.exception(f'Exception occurred while observing tasks: {[first_observe_coroutine, *other_coroutines]}', exc_info=True)
            raise MapperLifecycleError('observe task failed') from original_error


    async def _authorize(self, auth_params: dict[str, Any] | None, manage_lifecycle_backoff: Backoff, **kwargs: Any) -> None:

        need_login = not self.mapper.token

        conn_coroutine: Coroutine[Any, Any, None]
        if need_login:
            conn_coroutine = self._establish_connection(
                    auth_params=auth_params,
                    manage_lifecycle_backoff=manage_lifecycle_backoff,
                    close_firstly=True,
                    **kwargs
                )
        else:
            conn_coroutine = wait_for(
                self._establish_connection(
                    auth_params=auth_params,
                    manage_lifecycle_backoff=manage_lifecycle_backoff,
                    close_firstly=True,
                    **kwargs
                ),
                timeout=self.connect_timeout
            )

        self.mapper._authorized.clear()
        await self._observe_task(
            observer_coroutine=self._observe_auth_error(),
            first_observe_coroutine=conn_coroutine,
            )


    async def _authorize_cycle(self, auth_params: dict[str, Any] | None, manage_lifecycle_backoff: Backoff, **kwargs: Any) -> None:
        while True:
            try:
                try:

                    await self._authorize(auth_params=auth_params,
                                          manage_lifecycle_backoff=manage_lifecycle_backoff, **kwargs)
                    manage_lifecycle_backoff.reset()
                    break
                except asyncio.TimeoutError:
                    self._logger.warning('timeout while waiting for connection after error')
                    await manage_lifecycle_backoff.asleep()
                    continue
                except Exception as e:
                    self._logger.exception('establish connection failed')
                    await self._close()
                    await manage_lifecycle_backoff.asleep()
                    continue
            except BackoffError:
                self._logger.warning('backoff timeout while waiting for connection after error')
                manage_lifecycle_backoff.reset()

    async def _manage_lifecycle(self, auth_params: dict[str, Any] | None = None, **kwargs: Any) -> None:
        manage_lifecycle_backoff = Backoff(DEFAULT_BACKOFF_CONFIG)
        while True:
            if self._state in (
                _LifecycleStates.DISCONNECTED,
                _LifecycleStates.DISCONNECTING
            ):
                await self._authorize_cycle(auth_params=auth_params, manage_lifecycle_backoff=manage_lifecycle_backoff,
                                           **kwargs)
            current_error_state = await self._lifecycle_queue.get()
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

            await self._authorize_cycle(auth_params=auth_params, manage_lifecycle_backoff=manage_lifecycle_backoff,**kwargs)



    async def get_generation(self) -> int:
        async with self._generation_lock:
            return self._generation


    async def get_next_generation(self) -> int:
        return await self.get_generation() + 1


    async def _next_generation(self) -> int:
        async with self._generation_lock:
            self._generation += 1
            return self._generation


    async def _drain_failures(self) -> None:
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