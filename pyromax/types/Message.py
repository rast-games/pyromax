from .File import Video, Photo, File
from pyromax.mixins.ReplyMixin import ReplyMixin
from .Update import Update
from .OpcodeEnum import Opcode

from pydantic import ConfigDict, field_validator, Field, AliasPath, PrivateAttr, model_validator

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from ..api import MaxApi


class Message(Update, ReplyMixin):
    id: str
    text: str
    sender: int
    time: int
    type: str
    attaches: list

    type: str = Field(alias='type', validation_alias=AliasPath('link', 'type'), default='USER', exclude=True) # Can be "REPLY", "EDITED" or "USER"
    status: str | None = Field(default=None, exclude=True)

    opcode: ClassVar[int] = Opcode.PUSH_NOTIFICATION.value


    @field_validator('attaches', mode='after')
    @classmethod
    def attaches_to_model(cls, attaches: list) -> list[Video | Photo | File]:
        types_of_attaches = {
            'VIDEO': Video,
            'PHOTO': Photo,
            'FILE': File,
        }

        attaches_valid = []
        for attach in attaches:
            if attach['_type'] in types_of_attaches:
                attaches_valid.append(types_of_attaches[attach['_type']](**attach))
            else:
                attaches_valid.append(attach)
        return attaches_valid

    @model_validator(mode='after')
    def type_of_message(self):
        if self.status == 'EDITED':
            self.type = self.status

        return self

    @classmethod
    def from_update(cls, update: Update) -> 'Message':
        # self = cls.model_validate(**update.model_dump(), context=dict(max_api = update.max_api, chat_id = update.payload['chatId'], **update.payload['message']))
        self = cls(**update.model_dump(), **update.payload['message'], chat_id=update.payload['chatId'], max_api=update.max_api)
        # self.attaches = self.attaches_to_model(self.attaches)
        return self




    def __repr__(self):
        details = []
        for key, value in self.__dict__.items():
            details.append(f"{key}={value}")
        return '\n'.join(details)