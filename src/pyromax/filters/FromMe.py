from __future__ import annotations
from typing import Any, TYPE_CHECKING

from .base import Filter
from ..models import Message

if TYPE_CHECKING:
    from .. import BaseMaxObject, MaxApi


class FromMeFilter(Filter):

    @property
    def work_with(self) -> type[BaseMaxObject]:
        return Message

    async def _check(self, msg: Message, max_api: MaxApi = None) -> bool | dict[str, Any]:
        if not max_api:
            self._logger.warn('Required argument(max_api) not provided')
        if max_api.id == msg.sender_id:
            return True
        return False