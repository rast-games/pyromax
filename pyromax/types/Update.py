from pydantic import BaseModel, Field, AliasPath

from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from ..api.MaxApi import MaxApi


class Update(BaseModel):
    max_api: Any = Field(exclude=True)
    opcode: int
    type: str = Field(exclude=True, default=None)
    # chat_id: int = Field(validation_alias=AliasPath('payload', 'chatId'))
    payload: dict | None = None
    # def __init__(self, update: dict, max_api: 'MaxApi'):
    #
    #     from pprint import pprint
    #     pprint(update)
    #
    #     self.payload = update['payload']
        # self.mark = update['payload']['mark']
        # self.unread = update['payload']['unread']


