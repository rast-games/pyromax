from __future__ import annotations

import types
from typing import TYPE_CHECKING, Any

from .StandardMaxEventObserver import StandardMaxEventObserver, Update
from ...models import BaseMaxObject

if TYPE_CHECKING:
    from ..Router import Router

class UpdateMaxEventObserver(StandardMaxEventObserver):

    def __init__(self, router: Router, event_name: str, type_of_update: type[Update] | types.UnionType) -> None:
        super().__init__(router, event_name, BaseMaxObject)
        self.really_type_of_update: type[Update] | types.UnionType = type_of_update


    async def is_my_update(
            self,
            update: Update
    ) -> bool:
        return isinstance(update, self.really_type_of_update)