from typing import ClassVar

from pydantic import Field, model_validator

from .Update import Update
from .OpcodeEnum import Opcode


class MessageReactionUpdate(Update):

    opcode: ClassVar[int] = Opcode.MESSAGE_REACTION_UPDATE.value
    chat_id: int = Field(alias='chatId')
    message_id: int = Field(alias='messageId')

    type: str = Field(default=None)

    reaction_info: dict = Field(alias='reactionInfo')

    has_sender_info: bool = False

    @model_validator(mode='after')
    def validate_reaction_info(self):
        if self.reaction_info:
            self.type = 'MESSAGE_ADDED_REACTION'
        else:
            self.type = 'MESSAGE_DELETED_REACTION'

        return self


    @classmethod
    def from_update(cls, update: Update) -> 'MessageReactionUpdate':
        return cls(**update.payload, max_api=update.max_api)


    def edit_data(self, data: dict) -> dict:
        data[type(self)] = self
        return data
