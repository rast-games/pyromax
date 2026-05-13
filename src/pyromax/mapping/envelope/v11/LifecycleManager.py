from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING, Any
import logging

from ....utils import Backoff
from .constants import DEFAULT_BACKOFF_CONFIG
from ....exceptions import RestartMapperError, AlreadyFailedError, BackoffError, MapperCancelledError

if TYPE_CHECKING:
    from .Mapper import Mapper

class LifecycleManager:
    def __init__(self, mapper: Mapper, fallback_waiter_timeout: int = 30):
        self.mapper = mapper
        self._logger = logging.getLogger('LifecycleManagerEnvelopeMapperV11')
        self._manage_lifecycle_task: asyncio.Task | None = None
        self._fallback_waiter_task: asyncio.Task | None = None
        self._lifecycle_task_lock: asyncio.Lock = asyncio.Lock()
        self._mapper_correctly_running: asyncio.Event = asyncio.Event()
        self.__fallback_waiter_timeout = fallback_waiter_timeout
        # self._has_lifecycle_task: asyncio.Event = asyncio.Event()


    async def _fallback_waiter(self) -> None:
        """
        A fallback option in case of unforeseen situations and the protocol.failed event hanging.

        It doesn't throw any exceptions, it just hangs in the background and when the timeout expires, it restarts after waiting for the protocol.failed event.
        """
        while True:
            try:
                try:
                    await self.mapper.protocol.failed.wait()
                    await asyncio.wait_for(self._mapper_correctly_running.wait(), timeout=self.__fallback_waiter_timeout)
                except asyncio.TimeoutError:
                    self._logger.error('Fallback timeout')
                    self._logger.info('try to recover lifecycle task')
                    await self.stop()
                    await self.start()
                except Exception as e:
                    self._logger.error(f'Error in fallback waiter: {e.__class__.__name__}: {e}', exc_info=True)
                    self._logger.info('try to recover lifecycle task with uncaught exception')
                    await self.stop()
                    await self.start()
            # except BaseException as e:
            #     if e.__class__ == KeyboardInterrupt:
            #         raise e
            #     self._logger.error('outer error in fallback waiter')
            except Exception as e:
                self._logger.error(f'outer error in fallback waiter: {e.__class__.__name__}: {e}', exc_info=True)


    async def _manage_lifecycle(
            self,
            auth_params: dict[str, Any] | None = None,
            **kwargs: Any
    ) -> None:
        if auth_params is None:
            auth_params = {}
        while True:
            manage_lifecycle_backoff = Backoff(DEFAULT_BACKOFF_CONFIG)
            try:
                try:
                    from ....utils import debug_tasks
                    self._logger.debug(f'{debug_tasks()}')
                    self._logger.debug('closing protocol')
                    await self.mapper.close()
                    self._logger.debug('protocol closed')
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
                    self._mapper_correctly_running.set()
                    self._logger.debug('auth token sent')
                    await self.mapper.protocol.failed.wait()
                    self.mapper._authorized.clear()
                    self._mapper_correctly_running.clear()
                    self._logger.warning('catch protocol failed')
                    # from random import random
                    # if random() > 0.5:
                    #     print('sleeping')
                    #     await asyncio.sleep(30)
                    #     print('sleeped')
                    if self.mapper.token is None:
                        raise RuntimeError('Try a connect without token')
                except (RestartMapperError, AlreadyFailedError, BackoffError, MapperCancelledError) as e:
                    self._logger.warning('Start/restart error: %s', e, exc_info=True)
                    self._logger.debug('Failed to start/restart mapper')
                    self._logger.debug('starting/restarting mapper(again)...')
            finally:
                self._mapper_correctly_running.clear()
                self.mapper._authorized.clear()
                self.mapper.protocol.failed.set()

            # except Exception as e:
            #     self._logger.error(f'Error in manage lifecycle task: {e.__class__.__name__}: {e}', exc_info=True)


    async def _cancel_lifecycle_task(self) -> None:
        task = await self.get_lifecycle_task()
        if task:
            try:
                task.cancel()
                await task
            except Exception as e:
                self._logger.info('spread exception')
                self._logger.info(f'error in lifecycle task: {e.__class__.__name__}: {e}', exc_info=True)
                self._logger.debug('error in lifecycle task was intercepted')
            except asyncio.CancelledError:
                pass


    async def wait_lifecycle_task(self, auth_params: dict[str, Any] | None = None, **kwargs) -> None:
        if auth_params is None:
            auth_params = {}
        while True:
            self._logger.info('try a get lifecycle task')
            task = await self.get_lifecycle_task()
            if task is None or task.done():
                self._logger.warning('lifecycle task is None or done')
                self._logger.debug('restarting lifecycle manager')
                self._logger.debug('stopping lifecycle manager')
                await self.stop()
                self._logger.debug('lifecycle manager stopped')
                self._logger.debug('starting lifecycle manager')
                await self.start()
                task = await self.get_lifecycle_task()
                self._logger.debug('lifecycle manager started')

            if task:
                try:
                    await task
                except Exception as e:
                    self._logger.error(f'lifecycle manager exception: {e.__class__.__name__}: {e}', exc_info=True)
                except asyncio.CancelledError:
                    self._logger.warning('lifecycle task cancelled')
            await asyncio.sleep(0.5)

    async def start(self, auth_params: dict[str, Any] | None = None, **kwargs) -> None:
        if auth_params is None:
            auth_params = {}
        self._logger.debug('cancelling lifecycle task while starting')
        await self._cancel_lifecycle_task()
        self._logger.debug('lifecycle task cancelled while starting')
        self._logger.debug('create manage lifecycle task in background')
        task = asyncio.create_task(self._manage_lifecycle(auth_params=auth_params, **kwargs))
        await self.set_lifecycle_task(task)
        if self._fallback_waiter_task is None:
            self._logger.info('starting fallback waiter task')
            self._fallback_waiter_task = asyncio.create_task(self._fallback_waiter())
            self._logger.info('fallback waiter task started')
        self._logger.debug('manage lifecycle task was set')
        # self._has_lifecycle_task.set()
        # return task


    async def get_lifecycle_task(self):
        async with self._lifecycle_task_lock:
            return self._manage_lifecycle_task


    async def set_lifecycle_task(self, task: asyncio.Task | None):
        async with self._lifecycle_task_lock:
            self._manage_lifecycle_task = task


    async def stop(self):
        """
        stop manage lifecycle task
        """
        self._logger.debug('cancelling lifecycle task')
        await self._cancel_lifecycle_task()
        self._logger.debug('lifecycle task cancelled')
        await self.set_lifecycle_task(None)
        self._logger.debug('lifecycle manager stopped')


    async def full_stop(self):
        """Fully stop the lifecycle manager.

        stopping with fallback waiter
        """
        try:
            if self._fallback_waiter_task is not None:
                self._fallback_waiter_task.cancel()
                await self._fallback_waiter_task
        except asyncio.CancelledError:
            self._logger.warning('fallback waiter already cancelled')

        self._logger.info('fallback waiter stopped')
        await self.stop()



    async def notify_about_exception(self, exception: Exception) -> None:
        self._logger.debug('notify_about_exception %s', exception, exc_info=exception)
        await self._cancel_lifecycle_task()
        self._logger.debug('notify_about_exception manage lifecycle task was cancelled')


