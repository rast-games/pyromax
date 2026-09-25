from __future__ import annotations
from collections.abc import AsyncGenerator
from typing import Any, cast, Callable
from functools import partial

from ....protocol import Response
from ....exceptions import MapperApiError, GetUpdatesProtocolError
from .payloads.responses import ErrorMessageResponse
from .translate.ToDTO import update_translate
from ...registry import register_mapper
from .LifecycleManager import LifecycleManager
from .responses import FailedUpdateResponse


from .mixins import FullMixin
from ....models import BaseMaxObject


@register_mapper("EnvelopeV11")
class Mapper(FullMixin):
    async def _listen_updates(
        self,
        context: Any,
    ) -> AsyncGenerator[Response, None]:
        """Endless updates reader

        :param context: Runtime context used while processing the request.
        :type context: Any
        :yields: Items produced by the iterator.
        :ytype: AsyncGenerator[Response, None]
        :raises RuntimeError: If lifecycle manager not set.
        :raises MapperApiError: If the requested action cannot be completed.
        """
        async with self._update_listener_lock:

            while True:
                if self.max_api.shutdown_requested:
                    return
                try:
                    await self._mapper_connected.wait()
                    if self._lifecycle_manager is None:
                        raise RuntimeError("Lifecycle manager not set")
                    gen = await self._lifecycle_manager.get_generation()
                    updates = await self.protocol.get_updates()
                except GetUpdatesProtocolError as e:
                    if self.max_api.shutdown_requested:
                        return
                    if self._lifecycle_manager is None:
                        self._logger.warning(
                            "lifecycle manager not available, wait init"
                        )
                        await self._lifecycle_manager_inited.wait()
                        # self._lifecycle_manager: LifecycleManager
                        lifecycle_manager = cast(
                            LifecycleManager, self._lifecycle_manager
                        )
                        gen = await lifecycle_manager.get_generation()
                    if self._lifecycle_manager is None:
                        raise RuntimeError("lifecycle manager not set")
                    self._logger.error("get_updates failed: %s", e)
                    self._lifecycle_manager.notify_about_exception(
                        e,
                        generation=gen,
                        source="Mapper.listen_updates",
                    )
                    continue
                for update in updates:
                    if update.model_dump().get("error"):
                        error = ErrorMessageResponse(**update.model_dump(by_alias=True))
                        error_msg = f"""
                            error: {error.error},
                            title: {error.title},
                            localized_message: {error.localized_message},
                            message: {error.error_message}
                            """
                        exc = MapperApiError(error_msg)

                        # self._logger.error("MapperApiError: %s", exc)

                        yield FailedUpdateResponse(exc)
                        continue
                    # yield cast(Update, update_translate(update, context=context))
                    yield update

    def listen_updates(
        self, context: Any
    ) -> tuple[
        Callable[[Response], Response | BaseMaxObject], AsyncGenerator[Response, None]
    ]:
        """Listen for updates.

        :param context: Runtime context used while processing the request.
        :type context: Any
        :returns: Items produced by the iterator.
        :rtype: tuple[Callable[[Response], Response | BaseMaxObject], AsyncGenerator[Response, None]]
        """
        return partial(update_translate, context=context), self._listen_updates(
            context=context
        )
