import asyncio
from typing import Any, cast

from .....protocol.envelope import Envelope
from .....methods import BaseMaxApiMethod
from ..methods.immutable import BaseMethod
from .....exceptions import (
    MapperApiError,
    SendingProtocolError,
    MapperTransportError,
    MapperConnectError,
    ConnectProtocolError,
    MapperNotImplementedMethodError,
    MapperTransportNotSupportedForMethodError,
    RequestWasCancelledError,
)
from ..payloads.responses import ErrorMessageResponse
from ..translate.ErrorTranslate import translate_error_response
from ..methods.build_ins import build_method, method_names
from ..translate.high_level_methods_translate import (
    get_registry as get_methods_registry,
)


from .MixinProtocol import MixinProtocol


class TransportMixin(MixinProtocol):
    _keepalive_task: asyncio.Task[Any] | None = None

    async def connect(
        self,
    ) -> None:
        """Connect the mapper to its transport and initialize its lifecycle.

        :raises MapperConnectError: If the transport connection cannot be established.


        :raises RuntimeError: If lifecycle manager not initialized.
        """
        try:
            if self._lifecycle_manager is None:
                raise RuntimeError("Lifecycle manager not initialized")
            await self.protocol.connect(
                await self._lifecycle_manager.get_generation()
            )
        except ConnectProtocolError as e:
            self._logger.error("Connect failed", stack_info=True, exc_info=True)
            raise MapperConnectError("Connect failed") from e
        self._logger.debug("protocol connected")
        if self._keepalive_task is not None:
            self._logger.debug("have another keepalive task, cancel it")
            try:
                self._keepalive_task.cancel()
                await self._keepalive_task
            except asyncio.CancelledError:
                self._logger.debug(
                    "self.mapper.connect() -> self._keepalive_task.cancel() -> CancelledError"
                )
            self._logger.debug("keepalive task cancelled")
        self._logger.debug("start keepalive task")
        self._keepalive_task = asyncio.create_task(self._keepalive())
        self._logger.debug("keepalive task started")
        self._mapper_connected.set()

    async def close(
        self,
        pending_requests_exc: Exception | None = None,
    ) -> None:
        """Close."""
        if self._telemetry is not None:
            await self._telemetry.stop()

        self._mapper_connected.clear()
        self._authorized.clear()
        await self.protocol.close(
            pending_requests_exc,
        )
        keepalive_task: asyncio.Task[Any] | None = self._keepalive_task
        self._keepalive_task = None
        if keepalive_task is not None:
            try:
                keepalive_task.cancel()
                await asyncio.wait_for(keepalive_task, timeout=5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self._logger.debug("keepalive task already cancelled")

    def log(self, level: int, msg: str) -> None:
        """CRITICAL = 50
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

        :type level: int
        :type msg: str
        """
        self._logger.log(level, msg)

    async def send_raw(
        self,
        method: BaseMethod,
        data: dict[Any, Any] | None = None,
        check_errors: bool = False,
        timeout: int | float = 30,
    ) -> Envelope:
        """Send request without catching exceptions

        :raises MapperCancelledError: If the operation fails.
        :raises AlreadyFailedError: If the operation fails.
        :raises MapperApiError: If the operation fails.
        :raises MapperTransportError: If the operation fails.

        :param method: BaseMethod instance to process.
        :type method: BaseMethod
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any] | None
        :param check_errors: The check errors value.
        :type check_errors: bool
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        :raises MapperApiError: If resulting payload has error(s) and check_errors is True.
        :raises MapperTransportError: if sending was failed or if timeout is exceeded.
        # :raises MapperCancelledError: if cancelation passed.
        """
        if data is None:
            data = {}
        try:

            response_future = await self.protocol.send(
                method=method,
                data=data,
            )
        # except AlreadyCancelledError as e:
        #     raise MapperCancelledError("try a send after close") from e
        except SendingProtocolError as e:
            self._logger.exception(
                "send protocol error",
                exc_info=True,
                stack_info=True,
            )
            raise MapperTransportError("send failed") from e
        try:
            response = await asyncio.wait_for(response_future, timeout=timeout)
        except asyncio.TimeoutError as e:
            raise MapperTransportError("send timeout") from e
        except RequestWasCancelledError as e:
            self._logger.exception(
                "Send was cancelled, by EventRouter: %s",
                e,
                stack_info=True,
                exc_info=True,
            )
            raise MapperTransportError("send was cancelled") from e
        except Exception as e:
            self._logger.error(
                "Handled unknown exception, while raw sending=%s",
                e,
                exc_info=True,
                stack_info=True,
            )
            raise
        # except asyncio.CancelledError:
        #     # if asyncio.current_task().cancelling():
        #     #     raise
        #     self._logger.error(
        #         "response future was cancelled (Mapper.send_raw)",
        #         stack_info=True,
        #     )
        #     raise MapperCancelledError("try response was cancelled while wait it")
        if check_errors and response.payload.get("error"):
            error = ErrorMessageResponse(**response.payload)
            raise translate_error_response(
                error,
                app_version=getattr(self.user_agent, "app_version", None),
            )
        return response

    async def send_raw_with_running_wait(
        self,
        method: BaseMethod,
        data: dict[Any, Any] | None = None,
        timeout: int | float = 30,
    ) -> Envelope:
        """Send raw with running wait.

        :param method: BaseMethod instance to process.
        :type method: BaseMethod
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any] | None
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        if data is None:
            data = {}
        response = await self.send_raw(
            method=method,
            data=data,
            timeout=timeout,
        )
        return response

    async def send(
        self,
        method: BaseMethod,
        data: dict[Any, Any] | None = None,
        return_exception: bool = False,
        check_errors: bool = False,
        max_retries: int = 3,
        timeout: int | float = 30,
        wait_auth: bool = True,
    ) -> Envelope:
        """Execute a mapped method and return its response envelope.

        :raises MapperTransportError: If sending or receiving protocol data fails.
        :raises MapperCancelledError: If the request is cancelled.

        :param method: BaseMethod instance to process.
        :type method: BaseMethod
        :param data: Contextual data passed through the processing pipeline.
        :type data: dict[Any, Any] | None
        :param return_exception: The return exception value.
        :type return_exception: bool
        :param check_errors: The check errors value.
        :type check_errors: bool
        :param max_retries: The max retries value.
        :type max_retries: int
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        :raises RuntimeError: If lifecycle manager not initialized.
        """
        if data is None:
            data = {}

        storage = {"gen": -1}
        for _ in range(max_retries):
            try:
                await self._mapper_connected.wait()
                if wait_auth:
                    await self._authorized.wait()
                if self._lifecycle_manager is None:
                    raise RuntimeError("Lifecycle manager not initialized")
                gen = await self._lifecycle_manager.get_generation()
                storage["gen"] = gen
                response = await self.send_raw(
                    method=method,
                    data=data,
                    check_errors=check_errors,
                    timeout=timeout,
                )
                return response
            except MapperTransportError as e:
                if self._lifecycle_manager is None:
                    self._logger.exception("lifecycle manager not available, wait init")
                    await self._lifecycle_manager_inited.wait()

                if self._lifecycle_manager is None:
                    raise RuntimeError("Lifecycle manager not initialized")

                self._lifecycle_manager.notify_about_exception(
                    e,
                    generation=storage["gen"],
                    source="mapper.send",
                )
                msg = f"Request {method.__class__.__name__} was cancelled"
                self._logger.warning(msg, exc_info=True, stack_info=True)
                if return_exception:
                    raise MapperTransportError("Cancelled request") from e

            except MapperApiError as e:
                if check_errors:
                    raise e
                self._logger.exception(
                    f"Caught api exception when sending request: %s"
                    f"method: {method.__class__.__name__}",
                    e,
                    exc_info=True,
                    stack_info=True,
                )
                if self._lifecycle_manager is None:
                    self._logger.warning("lifecycle manager not available, wait init")
                    await self._lifecycle_manager_inited.wait()

                if self._lifecycle_manager is None:
                    raise RuntimeError("Lifecycle manager not initialized")
                self._lifecycle_manager.notify_about_exception(
                    e,
                    generation=storage["gen"],
                    source="mapper.send",
                )
                self._authorized.clear()
                if return_exception:
                    raise MapperTransportError(
                        "unknown exception was catch while send"
                    ) from e
            except Exception as e:
                self._logger.warning(
                    f"Caught exception when sending request: %s"
                    f"method: {method.__class__.__name__}",
                    e,
                    exc_info=True,
                    stack_info=True,
                )
                if self._lifecycle_manager is None:
                    self._logger.warning("lifecycle manager not available, wait init")
                    await self._lifecycle_manager_inited.wait()

                if self._lifecycle_manager is None:
                    raise RuntimeError("Lifecycle manager not initialized")
                self._lifecycle_manager.notify_about_exception(
                    e,
                    generation=storage["gen"],
                    source="mapper.send",
                )
                self._authorized.clear()
                if return_exception:
                    raise MapperTransportError(
                        "unknown exception was catch while send"
                    ) from e
        else:
            raise MapperTransportError(
                "max retries to send exceeded",
            )

    async def _call_build_in_method(
        self,
        method_name: method_names,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Call build in method.

        :param method_name: method_names instance to process.
        :type method_name: method_names
        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        """
        from ..Mapper import Mapper

        method = build_method(
            method_name=method_name, transport=self.protocol.transport
        )
        return await method(cast(Mapper, self), *args, **kwargs)

    async def call_method(
        self, method: type[BaseMaxApiMethod[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Call method.

        :param method: type[BaseMaxApiMethod[Any]] instance to process.
        :type method: type[BaseMaxApiMethod[Any]]
        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        :raises MapperNotImplementedMethodError: If method not supported for this mapper.
        :raises MapperApiError: If try call method on not initialized mapper(without user agent).
        :raises MapperTransportNotSupportedForMethodError: If method not supported for this transport.
        """
        from ..Mapper import Mapper

        methods_registry = get_methods_registry(cast(Mapper, self))
        method_with_device_types = methods_registry.get(method)
        if method_with_device_types is None:
            raise MapperNotImplementedMethodError(
                "Method not supported for this mapper"
            )
        if not self.user_agent:
            raise MapperApiError(
                "try call method on not initialized mapper(without user agent)"
            )
        bounded_method = method_with_device_types.get(self.user_agent.device_type)
        if bounded_method is None:
            raise MapperTransportNotSupportedForMethodError(
                "Method not supported for this transport"
            )

        return await bounded_method(
            *args,
            **kwargs,
        )
