from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict

from src.pyromax.models import BaseMaxObject
from src.pyromax.models.EmojiReaction import Counters


def to_camel_case(snake_str):

    words = snake_str.split('_')

    camel_case = [words[0].lower()] + [word.capitalize() for word in words[1:]]

    return ''.join(camel_case)


class CamelCaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel_case,
        validate_by_name=True
    )


class UserAgentModel(CamelCaseModel):
    device_type: str
    locale: str
    device_locale: str
    os_version: str
    device_name: str
    header_user_agent: str
    app_version: str
    screen: str
    timezone: str


class UserAgentPayload(CamelCaseModel):
    user_agent: UserAgentModel
    device_id: str


class AuthModel(CamelCaseModel):
    token: str
    chats_count: int
    interactive: bool
    chats_sync: int
    contacts_sync: int
    presence_sync: int
    drafts_sync: int


class MessageModel(CamelCaseModel):
    sender: int
    id: str
    time: int
    type: str
    cid: int
    attaches: list
    text: str | None = None
    status: str | None = None

class PushPayloadModel(CamelCaseModel):
    chat_id: int
    message: MessageModel
    ttl: bool
    mark: int
    unread: int | None
    prev_message_id: str | None = None


class ReactionInfoModel(CamelCaseModel):
    your_reaction: str | None = None
    total_count: int | None = None
    counters: list[dict] | None = None

class EmojiReactionUpdateModel(CamelCaseModel):
    chat_id: int
    message_id: str
    reaction_info: ReactionInfoModel


class CreateCellForFileModel(CamelCaseModel):
    count: int = 1

class BaseFile(BaseModel, ABC):

    data: bytes
    url: str | None = None

    @classmethod
    async def upload(cls, data: bytes):
        self = cls(data=data)

        await self.create_cell_for_file()

        await self.upload_data_to_url()


    @abstractmethod
    async def upload_data_to_url(self): pass


    @abstractmethod
    async def create_cell_for_file(self): pass



class Photo(BaseFile):
    pass
    # async def upload(self): pass


class Video(BaseFile):
    # async def upload(self): pass
    pass


class File(BaseFile):
    # async def upload(self): pass
    pass

