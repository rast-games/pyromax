from __future__ import annotations
from typing import Any, TYPE_CHECKING

from typing_extensions import Self

from pydantic import BaseModel, PrivateAttr

if TYPE_CHECKING:
    from .client import MaxApi


class ContextController(BaseModel):
    """Base model that can be bound to a MaxApi instance."""

    _max_api: MaxApi | None = PrivateAttr()


    def model_post_init(self, __context: Any) -> None:
        """Store the bot instance from Pydantic context if present."""
        self._max_api = __context.get("max_api") if __context else None

    def as_(self, max_api: MaxApi | None) -> Self:
        """Bind object to a bot instance.

        Parameters
        ----------
        max_api
            MaxApi instance.

        Returns
        -------
        Self
            Self with bound bot.
        """
        self._max_api = max_api
        return self

    @property
    def bot(self) -> MaxApi | None:
        """Return the bound bot instance."""
        return self._max_api