from pydantic import BaseModel, Field, AliasPath

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from ..api.MaxApi import MaxApi


class Update(BaseModel):
    max_api: Any = Field(exclude=True)
    opcode: int
    type: str = Field(exclude=True, default=None)
    payload: dict | None = Field(default=None, exclude=True)


