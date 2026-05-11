from __future__ import annotations
from collections.abc import AsyncGenerator
from typing import Any, TYPE_CHECKING, cast

from ....exceptions import MapperApiError
from .payloads.responses import ErrorMessageResponse
from .translate.ToDTO import update_translate
from ...registry import register_mapper
from ....dispatcher.event.UpdateType import Update


from .mixins import FullMixin

if TYPE_CHECKING:
    from ....models import MessageLink
    from ....core import MaxApi


@register_mapper('EnvelopeV11')
class Mapper(FullMixin):
    async def listen_updates(
            self,
            context: Any,
    ) -> AsyncGenerator[Update, None]:
        """Endless updates reader"""
        async with self._update_listener_lock:
            while True:
                try:
                    updates = await self.protocol.get_updates()
                except RuntimeError as e:
                    self._logger.error('get_updates failed: %s', e)
                    continue
                for update in updates:
                    if update.model_dump().get('error'):
                        error = ErrorMessageResponse(**update.model_dump(by_alias=True))
                        error_msg = \
                            f"""
                            error: {error.error},
                            title: {error.title},
                            localized_message: {error.localized_message},
                            message: {error.message}
                            """
                        raise MapperApiError(error_msg)
                    yield cast(Update, update_translate(update, context=context))