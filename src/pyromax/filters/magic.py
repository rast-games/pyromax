from __future__ import annotations

from typing import Any, TYPE_CHECKING, cast

from .base import Filter
from ..models import BaseMaxObject

from magic_filter import MagicFilter as _MagicFilter

if TYPE_CHECKING:
    from .base import Update

class AlwaysEqual:
    def __eq__(self, other: Any) -> bool:
        return True

class MagicFilter(_MagicFilter, Filter): #type: ignore[misc]
    _SKIP_CHECK_PREPARATIONS: bool = True

    @property
    def work_with(self) -> tuple[type[BaseMaxObject]]: return cast(tuple[type[BaseMaxObject]], (AlwaysEqual(),))

    async def _check(self, update: Update, *args: Any, **kwargs: Any) -> bool: return self.resolve(update)


F = MagicFilter()