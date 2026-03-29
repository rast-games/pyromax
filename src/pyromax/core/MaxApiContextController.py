from __future__ import annotations
from typing import Any, TYPE_CHECKING

from typing_extensions import Self

from pydantic import BaseModel, PrivateAttr

if TYPE_CHECKING:
    from src.pyromax.core.client import MaxApi


class ContextController(BaseModel):

    _max_api: MaxApi | None = PrivateAttr()


    def model_post_init(self, __context: Any) -> None:
        self._max_api = __context.get("max_api") if __context else None

    def as_(self, max_api: MaxApi | None) -> Self:
        """
        Bind object to a bot instance.

        :param max_api: MaxApi instance
        :return: self
        """
        self._max_api = max_api
        return self

    @property
    def bot(self) -> MaxApi | None:
        """
        Get bot instance.

        :return: Bot instance
        """
        return self._max_api