import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any, cast

from .....protocol.envelope import EnvelopeProtocol, Envelope
from ..methods.immutable import BaseMethod
from .....exceptions import AlreadyFailedError, AlreadyCancelledError, MapperCancelledError, MapperApiError, SendingProtocolError, MapperTransportError, MapperConnectError, ConnectProtocolError
from ..payloads.responses import ErrorMessageResponse
from ..methods.build_ins import build_method, method_names


class TransportMixin:

    protocol: EnvelopeProtocol
    _logger: logging.Logger
    _keepalive_task: asyncio.Task
    _keepalive: Callable[..., Coroutine[Any, Any, Any]]
    _authorized: asyncio.Event
    _lifecycle_manager: 'LifecycleManager'

    async def connect(
            self,
    ) -> None:
        """
        Raises
        ------
            MapperConnectError
        """
        try:

            await self.protocol.connect()
        except ConnectProtocolError as e:
            self._logger.error('Connect failed', stack_info=True, exc_info=True)
            raise MapperConnectError('Connect failed') from e
        self._logger.debug('protocol connected')
        if self._keepalive_task:
            self._logger.debug('have another keepalive task, cancel it')
            try:
                self._keepalive_task.cancel()
                await self._keepalive_task
            except asyncio.CancelledError:
                self._logger.debug(f'self.mapper.connect() -> self._keepalive_task.cancel() -> CancelledError')
            self._logger.debug('keepalive task cancelled')
        self._logger.debug('start keepalive task')
        self._keepalive_task = asyncio.create_task(self._keepalive())
        self._logger.debug('keepalive task started')

    async def close(
            self,
    ) -> None:
        await self.protocol.close()

        if self._keepalive_task:

            try:
                self._keepalive_task.cancel()
                await self._keepalive_task
            except asyncio.CancelledError:
                self._logger.debug('keepalive task already cancelled')

    def log(self, level: int, msg: str) -> None:
        """
        CRITICAL = 50
        FATAL = CRITICAL
        ERROR = 40
        WARNING = 30
        WARN = WARNING
        INFO = 20
        DEBUG = 10
        NOTSET = 0

        :param level:
        :param msg:
        :return:
        """
        self._logger.log(level, msg)

    async def send_raw(self, method: BaseMethod, data: dict[Any, Any] | None = None,
                       check_errors: bool = False) -> Envelope:
        """Send request without catching exceptions

        Raises
        ------
            MapperCancelledError
            AlreadyFailedError
            MapperApiError
            MapperTransportError
        """
        if data is None:
            data = {}

        if self.protocol.failed.is_set():
            raise AlreadyFailedError('Mapper protocol already failed, need restart')
        try:

            response_future = await self.protocol.send(
                method=method,
                data=data,
            )
        except AlreadyCancelledError as e:
            raise MapperCancelledError('try a send after close') from e
        except SendingProtocolError as e:
            self._logger.debug('send protocol error', exc_info=True)
            raise MapperTransportError('send failed') from e
        try:
            response = await response_future
        except asyncio.CancelledError:
            raise MapperCancelledError('try response was cancelled while wait it')
        if check_errors and response.payload.get('error'):
            error = ErrorMessageResponse(**response.payload)
            error_msg = \
                f"""
            error: {error.error},
            title: {error.title},
            localized_message: {error.localized_message},
            message: {error.error_message}

            """
            error_obj = MapperApiError(error_msg)
            error_obj.title = error.title
            error_obj.localized_message = error.localized_message
            error_obj.message = error.error_message
            error_obj.error = error.error
            raise error_obj
        return response

    async def send_raw_with_running_wait(self, method: BaseMethod, data: dict[Any, Any] | None = None) -> Envelope:
        if data is None:
            data = {}
        await self.protocol.running.wait()
        response = await self.send_raw(method=method, data=data)
        return response

    async def send(self, method: BaseMethod, data: dict[Any, Any] | None = None,
                   return_exception: bool = False) -> Envelope:
        """
        Raises
        ------
            MapperTransportError
            MapperCancelledError
        """
        if data is None:
            data = {}
        while True:
            try:
                await self.protocol.running.wait()
                await self._authorized.wait()
                response = await self.send_raw(method=method, data=data)
                return response
            except (MapperCancelledError, AlreadyFailedError) as e:
                await self._lifecycle_manager.notify_about_exception(e)

                self._logger.warning(f'Request {method.__class__.__name__} was cancelled', exc_info=True, stack_info=True)
                if return_exception:
                    raise MapperCancelledError('Cancelled request') from e
            except Exception as e:
                self._logger.warning(f'Caught exception when sending request: %s'
                                      f'method: {method.__class__.__name__}', e, exc_info=True, stack_info=True)
                await self._lifecycle_manager.notify_about_exception(e)
                self._authorized.clear()
                if return_exception:
                    raise MapperTransportError('unknown exception was catch while send') from e

    async def _call_build_in_method(
            self,
            method_name: method_names,
            *args: Any,
            **kwargs: Any,
    ):
        from ..Mapper import Mapper
        method = build_method(method_name=method_name, transport=self.protocol.transport)
        return await method(mapper=cast(Mapper, self),*args, **kwargs)