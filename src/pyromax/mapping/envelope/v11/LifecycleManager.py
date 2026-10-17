from __future__ import annotations
import asyncio
from asyncio import wait_for
from collections.abc import Callable, Generator
from typing import TYPE_CHECKING, Any, Coroutine
import logging
from enum import Enum

from ....utils import Backoff
from ....models import DisconnectEvent, UnsupportedClientVersionEvent
from .constants import DEFAULT_BACKOFF_CONFIG
from ....exceptions import (
    RestartMapperError,
    BackoffError,
    MapperLifecycleError,
    MapperConnectError,
    MapperRestartCycleError,
    NeedReloginMapperError,
    UnsupportedClientVersionMapperError,
    AuthInputRequired,
)

if TYPE_CHECKING:
    from .Mapper import Mapper


class _LifecycleStates(Enum):
    CONNECTED = 1
    CONNECTING = 2
    DISCONNECTED = 3
    DISCONNECTING = 4


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
        need_login: bool = False,
    ):
        """Initialize the lifecycle manager.

        :param mapper: Mapper backend or mapper instance.
        :type mapper: Mapper
        :param connect_timeout: The connect timeout value.
        :type connect_timeout: int | None
        """
        if connect_timeout is None:
            connect_timeout = 5
        self.mapper = mapper
        self._need_login = need_login
        self._logger = logging.getLogger("LifecycleManagerEnvelopeMapperV11")
        self._manage_lifecycle_task: asyncio.Task[Any] | None = None
        self.connect_timeout = connect_timeout

        self._lifecycle_queue: asyncio.Queue[LifecycleFailure] = asyncio.Queue(
            maxsize=1
        )
        self._generation: int = 0
        self._generation_lock: asyncio.Lock = asyncio.Lock()
        self._state: _LifecycleStates = _LifecycleStates.DISCONNECTED
        self._only_send_user_agent = False
        self._unsupported_app_versions: set[str] = set()

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
                "failure already queued, dropping duplicate from %s",
                source,
            )
            self._logger.debug(
                LifecycleFailure(
                    generation=generation,
                    exception=exception,
                    source=source,
                )
            )

    def start(self, auth_params: dict[str, Any] | None = None, **kwargs: Any) -> None:
        """Start.

        :param auth_params: dict[str, Any] instance to process.
        :type auth_params: dict[str, Any] | None
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        """
        task = self._manage_lifecycle_task

        if task is not None and not task.done():
            return

        if auth_params is None:
            auth_params = {}

        self._manage_lifecycle_task = asyncio.create_task(
            self._manage_lifecycle(auth_params=auth_params, **kwargs)
        )

    async def stop(self) -> None:
        task = self._manage_lifecycle_task
        self._manage_lifecycle_task = None
        try:
            if task is not None and not task.done():
                task.cancel()
                await task
        except asyncio.CancelledError:
            pass
        finally:
            await self._close()

    async def wait_until_connected(self) -> None:
        """Wait for the initial connection and propagate lifecycle failures."""
        lifecycle_task = self._manage_lifecycle_task
        if lifecycle_task is None:
            raise RuntimeError("Lifecycle manager is not started")

        connected_task = asyncio.create_task(self.mapper._protocol_connected.wait())
        try:
            done, _ = await asyncio.wait(
                (connected_task, lifecycle_task),
                return_when=asyncio.FIRST_COMPLETED,
            )
            if lifecycle_task in done:
                await lifecycle_task
        finally:
            if not connected_task.done():
                connected_task.cancel()
                await asyncio.gather(connected_task, return_exceptions=True)

    async def request_reconnect(self, exception: Exception) -> None:
        """Queue a reconnect and wait until the new connection is established."""
        if self._state is not _LifecycleStates.CONNECTED:
            return

        generation = await self.get_generation()
        self.mapper._protocol_connected.clear()
        self.notify_about_exception(
            exception,
            generation=generation,
            source="LifecycleManager.request_reconnect",
        )
        await self.wait_until_connected()

    async def _close(
        self,
        pending_requests_exc: Exception | None = None,
    ) -> None:
        """Close."""
        protocol_connected = getattr(self.mapper, "_protocol_connected", None)
        if protocol_connected is not None:
            protocol_connected.clear()
        try:
            await self.mapper.close(pending_requests_exc)
        except Exception:
            self._logger.exception("close failed")

    async def _handle_disconnect(self, exception: Exception) -> bool:
        """Close the failed connection, notify handlers, and wait to reconnect."""
        try:
            self._state = _LifecycleStates.DISCONNECTING
            await self._close(exception)
        finally:
            self._state = _LifecycleStates.DISCONNECTED

        reconnect = self.mapper.extra_config.reconnect
        delay = self.mapper.extra_config.reconnect_delay
        await self.mapper.max_api._emit_disconnect(
            DisconnectEvent(
                exception=exception,
                reconnect=reconnect,
                delay=delay,
            )
        )

        if not reconnect:
            return False

        await asyncio.sleep(delay)
        return True

    async def _handle_unsupported_version(
        self,
        exception: UnsupportedClientVersionMapperError,
    ) -> None:
        """Notify handlers and select a replacement when none was chosen."""
        max_api = self.mapper.max_api
        rejected_version = exception.app_version or max_api.app_version
        if rejected_version is not None:
            self._unsupported_app_versions.add(rejected_version)

        available_versions = await max_api.get_available_app_versions()
        await max_api._emit_unsupported_version(
            UnsupportedClientVersionEvent(
                exception=exception,
                app_version=rejected_version,
                available_versions=available_versions,
            )
        )

        if (
            max_api.app_version == rejected_version
            and self.mapper.extra_config.autochange_app_version_if_current_unsupported
        ):
            selected_version = await max_api.set_random_app_version(
                reconnect=False,
                exclude=tuple(self._unsupported_app_versions),
            )
            self._logger.warning(
                "Application version %s is unsupported; selected %s",
                rejected_version,
                selected_version,
            )

    async def _connect(
        self,
        manage_lifecycle_backoff: Backoff,
        auth_params: dict[str, Any] | None = None,
        only_send_user_agent: bool = False,
        **kwargs: Any,
    ) -> None:
        """Connect.

        :param manage_lifecycle_backoff: Backoff instance to process.
        :type manage_lifecycle_backoff: Backoff
        :param auth_params: dict[str, Any] instance to process.
        :type auth_params: dict[str, Any] | None
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :raises MapperRestartCycleError: if connect failed and need restart.
        """
        if auth_params is None:
            auth_params = {}
        only_send_user_agent = only_send_user_agent or self._only_send_user_agent
        if only_send_user_agent:
            self._only_send_user_agent = True
        try:
            await self.mapper.connect()
        except MapperConnectError as e:
            raise MapperRestartCycleError("Connect failed") from e
        send_user_agent = True
        if (
            not self.mapper.logged or not self.mapper.token
        ) and not only_send_user_agent:
            resp = await self.mapper.login(
                login_backoff=manage_lifecycle_backoff,
                **kwargs,
            )
            self.mapper.logged = True
            if resp is not None:
                send_user_agent = False

        token = self.mapper.token
        user_agent = self.mapper.user_agent

        if only_send_user_agent:
            assert user_agent is not None
            try:
                await self.mapper._send_only_user_agent(
                    user_agent=user_agent,
                )
            except RestartMapperError as e:
                if self.mapper.max_api.shutdown_requested:
                    raise asyncio.CancelledError from e
                self._logger.exception("Exception while try to connect=%s", e)
                raise MapperRestartCycleError("Send user agent failed") from e
        else:
            assert token is not None
            assert user_agent is not None
            try:
                await self.mapper._auth(
                    token=token,
                    user_agent=user_agent,
                    send_user_agent=send_user_agent,
                    **auth_params,
                )
            except NeedReloginMapperError as e:
                if self.mapper.max_api.shutdown_requested:
                    raise asyncio.CancelledError from e
                self.mapper.logged = False
                self.mapper._authorized.clear()
                if not self.mapper.extra_config.relogin:
                    self._need_login = False
                    self._only_send_user_agent = True
                    self._logger.warning(
                        "Login token was rejected; reconnecting without "
                        "authorization: %s",
                        e,
                    )
                    raise

                self._need_login = True
                self._logger.warning("Login token was rejected: %s", e)
                raise
            except RestartMapperError as e:
                if self.mapper.max_api.shutdown_requested:
                    raise asyncio.CancelledError from e
                self._logger.exception("Exception while try to connect=%s", e)
                raise MapperRestartCycleError("Auth failed") from e
            self.mapper._authorized.set()
            self._logger.debug("Auth token sent")

    async def _establish_connection(
        self,
        manage_lifecycle_backoff: Backoff,
        auth_params: dict[str, Any] | None = None,
        close_firstly: bool = True,
        exception: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        # from random import random
        #
        # rnd = random()
        # print(rnd)
        # if rnd > 0.5:
        #     print("sleeping")
        #     await asyncio.sleep(20)

        """Establish connection.

        :param manage_lifecycle_backoff: Backoff instance to process.
        :type manage_lifecycle_backoff: Backoff
        :param auth_params: dict[str, Any] instance to process.
        :type auth_params: dict[str, Any] | None
        :param close_firstly: The close firstly value.
        :type close_firstly: bool
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        """
        try:
            if close_firstly:
                self._state = _LifecycleStates.DISCONNECTING
                await self._close(exception)
                self._state = _LifecycleStates.DISCONNECTED
            self._state = _LifecycleStates.CONNECTING
            try:
                await self._connect(
                    manage_lifecycle_backoff=manage_lifecycle_backoff,
                    auth_params=auth_params,
                    **kwargs,
                )
            except (NeedReloginMapperError, UnsupportedClientVersionMapperError):
                raise
            except RestartMapperError as e:
                self._logger.exception("Connect failed with exception=%s", e)
                raise MapperLifecycleError("NeedRestartMapper") from e
            except MapperRestartCycleError:
                raise

            self._state = _LifecycleStates.CONNECTED
            self.mapper._protocol_connected.set()
        except UnsupportedClientVersionMapperError:
            # The authorize cycle owns disconnect handling for this domain
            # error.  Propagate it before awaiting close(), otherwise a
            # concurrent reader failure can cancel this task and replace the
            # useful API error with MapperLifecycleError.
            raise
        except Exception as e:
            try:
                self._state = _LifecycleStates.DISCONNECTING
                await self._close(exception)
            finally:
                self._state = _LifecycleStates.DISCONNECTED

            if not isinstance(
                e,
                (NeedReloginMapperError, UnsupportedClientVersionMapperError),
            ):
                self._logger.exception("Connection failed", exc_info=True)
            raise
        except asyncio.CancelledError:
            try:
                self._state = _LifecycleStates.DISCONNECTING
                await self._close(exception)
            finally:
                self._state = _LifecycleStates.DISCONNECTED
            self._logger.warning("connection cancelled")
            raise

    async def _observe_auth_error(self) -> None:
        """Observe auth error.

        :raises MapperLifecycleError: If _observe_error.
        """
        while True:
            gen = await self.get_generation()
            if not self.mapper._authorized.is_set():
                error_state = await self._lifecycle_queue.get()
            else:
                return
            if error_state and error_state.generation != gen:
                continue
            # A server may send a domain error response and close the socket in
            # the same event-loop iteration.  Give the request consumer a turn
            # to surface that specific error before this generic transport
            # observer cancels the connection task.
            await asyncio.sleep(0)
            if not self.mapper._authorized.is_set():
                raise MapperLifecycleError("_observe_error") from error_state.exception
            elif self.mapper._authorized.is_set():
                try:
                    self._lifecycle_queue.put_nowait(error_state)
                except asyncio.QueueFull:
                    pass

    async def _observe_task(
        self,
        observer_factory: Callable[[], Coroutine[Any, Any, None]],
        first_observe_factory: Callable[[], Coroutine[Any, Any, Any]],
        *other_factories: Callable[[], Coroutine[Any, Any, Any]],
    ) -> None:
        """Observe task.

        :param observer_coroutine: Coroutine[Any, Any, None] instance to process.
        :type observer_coroutine: Coroutine[Any, Any, None]
        :param first_observe_coroutine: Coroutine[Any, Any, Any] instance to process.
        :type first_observe_coroutine: Coroutine[Any, Any, Any]
        :param other_coroutines: Coroutine[Any, Any, Any] instance to process.
        :type other_coroutines: Coroutine[Any, Any, Any]
        :raises MapperLifecycleError: If observe task failed.
        """
        try:
            all_factories = [first_observe_factory, *other_factories]
            async with asyncio.TaskGroup() as tg:
                observe_task = tg.create_task(observer_factory())
                main_tasks = []
                for factory in all_factories:
                    main_tasks.append(tg.create_task(factory()))
                await asyncio.gather(*main_tasks)
                observe_task.cancel()

        except BaseExceptionGroup as group:
            exceptions = tuple(self._flatten_exception_group(group))
            for error_type in (
                NeedReloginMapperError,
                UnsupportedClientVersionMapperError,
                AuthInputRequired,
            ):
                domain_error = next(
                    (exc for exc in exceptions if isinstance(exc, error_type)),
                    None,
                )
                if domain_error is not None:
                    raise domain_error

            cancelled_error = next(
                (
                    exc
                    for exc in exceptions
                    if isinstance(exc, asyncio.CancelledError)
                ),
                None,
            )
            if cancelled_error is not None:
                raise cancelled_error

            original_error = exceptions[0] if exceptions else group
            self._logger.exception(
                "Exception occurred while observing lifecycle tasks",
                exc_info=True,
            )
            raise MapperRestartCycleError("observe task failed") from original_error

    @staticmethod
    def _flatten_exception_group(
        exception: BaseException,
    ) -> Generator[BaseException, None, None]:
        """Yield leaf exceptions from a possibly nested exception group."""
        if isinstance(exception, BaseExceptionGroup):
            for nested_exception in exception.exceptions:
                yield from LifecycleManager._flatten_exception_group(
                    nested_exception
                )
            return
        yield exception

    async def _authorize(
        self,
        auth_params: dict[str, Any] | None,
        manage_lifecycle_backoff: Backoff,
        exception: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        """Authorize.

        :param auth_params: dict[str, Any] instance to process.
        :type auth_params: dict[str, Any] | None
        :param manage_lifecycle_backoff: Backoff instance to process.
        :type manage_lifecycle_backoff: Backoff
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        """
        need_login = self._need_login

        connection_factory: Callable[[], Coroutine[Any, Any, Any]]
        if need_login:

            def connection_factory() -> Coroutine[Any, Any, None]:
                return self._establish_connection(
                    auth_params=auth_params,
                    manage_lifecycle_backoff=manage_lifecycle_backoff,
                    close_firstly=True,
                    exception=exception,
                    **kwargs,
                )

            self._need_login = True
        else:

            def connection_factory() -> Coroutine[Any, Any, None]:
                return wait_for(
                    self._establish_connection(
                        auth_params=auth_params,
                        manage_lifecycle_backoff=manage_lifecycle_backoff,
                        close_firstly=True,
                        exception=exception,
                        **kwargs,
                    ),
                    timeout=self.connect_timeout,
                )

        # Allocate the generation before starting either task.  Failed
        # connection attempts must consume a generation too: their reader
        # callbacks may arrive after the next attempt has already started.
        # Reusing the same number would make that stale transport failure look
        # as if it belonged to the new connection.
        await self._next_generation()
        self.mapper._authorized.clear()
        try:
            await self._observe_task(
                observer_factory=self._observe_auth_error,
                first_observe_factory=connection_factory,
            )
        except NeedReloginMapperError:
            raise
        except UnsupportedClientVersionMapperError:
            raise
        except MapperRestartCycleError:
            raise
        except Exception as e:
            self._logger.exception(
                "got an unexpected exception while observe task=%s",
                e,
                exc_info=True,
                stack_info=True,
            )
            raise

    async def _authorize_cycle(
        self,
        auth_params: dict[str, Any] | None,
        manage_lifecycle_backoff: Backoff,
        exception: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        """Authorize cycle.

        :param auth_params: dict[str, Any] instance to process.
        :type auth_params: dict[str, Any] | None
        :param manage_lifecycle_backoff: Backoff instance to process.
        :type manage_lifecycle_backoff: Backoff
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        """
        while True:
            try:
                try:

                    await self._authorize(
                        auth_params=auth_params,
                        manage_lifecycle_backoff=manage_lifecycle_backoff,
                        exception=exception,
                        **kwargs,
                    )
                    manage_lifecycle_backoff.reset()
                    break
                except asyncio.TimeoutError as e:
                    self._logger.warning(
                        "timeout while waiting for connection after error"
                    )
                    if not await self._handle_disconnect(e):
                        raise
                    continue
                except NeedReloginMapperError as e:
                    if not self.mapper.extra_config.relogin:
                        if not await self._handle_disconnect(e):
                            raise
                    continue
                except UnsupportedClientVersionMapperError as e:
                    await self._handle_unsupported_version(e)
                    if not await self._handle_disconnect(e):
                        raise
                    continue
                except MapperRestartCycleError as e:
                    if not await self._handle_disconnect(e):
                        raise
                    continue
                except Exception:
                    self._logger.exception("establish connection failed")
                    await self._close(exception)
                    raise
                except asyncio.CancelledError:
                    raise
            except BackoffError:
                self._logger.warning(
                    "backoff timeout while waiting for connection after error"
                )
                manage_lifecycle_backoff.reset()

    async def _manage_lifecycle(
        self, auth_params: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Manage lifecycle.

        :param auth_params: dict[str, Any] instance to process.
        :type auth_params: dict[str, Any] | None
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        """
        manage_lifecycle_backoff = Backoff(DEFAULT_BACKOFF_CONFIG)
        while True:
            if self._state in (
                _LifecycleStates.DISCONNECTED,
                _LifecycleStates.DISCONNECTING,
            ):
                await self._authorize_cycle(
                    auth_params=auth_params,
                    manage_lifecycle_backoff=manage_lifecycle_backoff,
                    **kwargs,
                )
            current_error_state = await self._lifecycle_queue.get()
            self._logger.warning("catch protocol failed")
            msg = (
                f"error: {current_error_state.exception},"
                f"source: {current_error_state.source},"
                f"gen: {current_error_state.generation},"
            )
            self._logger.error(msg)
            if current_error_state.generation != await self.get_generation():
                continue

            if not await self._handle_disconnect(current_error_state.exception):
                self.mapper.max_api.request_shutdown()
                return
            await self._authorize_cycle(
                auth_params=auth_params,
                manage_lifecycle_backoff=manage_lifecycle_backoff,
                exception=current_error_state.exception,
                **kwargs,
            )

    async def get_generation(self) -> int:
        """Retrieve generation.

        :returns: The resulting int value.
        :rtype: int
        """
        async with self._generation_lock:
            return self._generation

    async def get_next_generation(self) -> int:
        """Retrieve next generation.

        :returns: The resulting int value.
        :rtype: int
        """
        return await self.get_generation() + 1

    async def _next_generation(self) -> int:
        """Next generation.

        :returns: The resulting int value.
        :rtype: int
        """
        async with self._generation_lock:
            self._generation += 1
            return self._generation
