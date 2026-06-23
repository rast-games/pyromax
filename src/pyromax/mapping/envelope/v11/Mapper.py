from __future__ import annotations
from collections.abc import AsyncGenerator
from typing import Any, cast, Callable
from functools import partial

from ....protocol import Response
from ....protocol.envelope import Envelope
from ....exceptions import MapperApiError
from .payloads.responses import ErrorMessageResponse
from .translate.ToDTO import update_translate
from ...registry import register_mapper
from ....dispatcher.event.UpdateType import Update


from .mixins import FullMixin
from ....models import BaseMaxObject


# if TYPE_CHECKING:
#     from ....models import MessageLink
#     from ....core import MaxApi


@register_mapper('EnvelopeV11')
class Mapper(FullMixin):
    async def _listen_updates(
            self,
            context: Any,
    ) -> AsyncGenerator[Update, None]:
        """Endless updates reader"""
        async with self._update_listener_lock:

            while True:
                try:
                    await self._mapper_connected.wait()
                    if self._lifecycle_manager is None:
                        raise RuntimeError('Lifecycle manager not set')
                    gen = await self._lifecycle_manager.get_generation()
                    updates = await self.protocol.get_updates()
                except RuntimeError as e:
                    if self._lifecycle_manager is None:
                        self._logger.warning('lifecycle manager not available, wait init')
                        await self._lifecycle_manager_inited.wait()
                    self._logger.error('get_updates failed: %s', e)
                    self._lifecycle_manager.notify_about_exception( #type: ignore[union-attr]
                        e,
                        generation=gen,
                        source='Mapper.listen_updates',
                    )
                    continue
                for update in updates:
                    if update.model_dump().get('error'):
                        error = ErrorMessageResponse(**update.model_dump(by_alias=True))
                        error_msg = \
                            f"""
                            error: {error.error},
                            title: {error.title},
                            localized_message: {error.localized_message},
                            message: {error.error_message}
                            """
                        raise MapperApiError(error_msg)
                    # yield cast(Update, update_translate(update, context=context))
                    yield update


    def listen_updates(self, context: Any) -> tuple[Callable[[Envelope], Envelope | BaseMaxObject], AsyncGenerator[Envelope, None]]:
        return partial(update_translate, context=context), self._listen_updates(context=context)