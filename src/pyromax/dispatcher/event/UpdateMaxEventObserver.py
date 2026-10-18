from __future__ import annotations

import types
from typing import TYPE_CHECKING

from .StandardMaxEventObserver import StandardMaxEventObserver
from .UpdateType import Update, MaxObject
from ...protocol import Response

if TYPE_CHECKING:
    from ..Router import Router


class UpdateMaxEventObserver(StandardMaxEventObserver[Response]):

    def __init__(
        self,
        router: Router,
        event_name: str,
        type_of_update: type[MaxObject] | types.UnionType,
    ) -> None:
        """Initialize the update max event observer.

        :param router: Router instance to process.
        :type router: Router
        :param event_name: The event name value.
        :type event_name: str
        :param type_of_update: type[MaxObject] | types.UnionType instance to process.
        :type type_of_update: type[MaxObject] | types.UnionType
        """
        super().__init__(router, event_name, Response)
        self.really_type_of_update: type[MaxObject] | types.UnionType = type_of_update

    async def is_my_update(self, update: Update) -> bool:
        """Return whether my update.

        :param update: Incoming update to process.
        :type update: Update
        :returns: True when the requested condition is satisfied; otherwise False.
        :rtype: bool
        """
        return isinstance(update, self.really_type_of_update)
