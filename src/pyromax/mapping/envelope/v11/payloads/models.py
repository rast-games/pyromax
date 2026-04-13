from __future__ import annotations

from typing import Annotated, Literal, Any

from pydantic import Field, BeforeValidator

from .shared import CamelCaseModel

import time

class UserAgentMappingModel(CamelCaseModel):
    device_type: str
    locale: str
    device_locale: str
    os_version: str
    device_name: str
    header_user_agent: str
    app_version: str
    screen: str
    timezone: str


class AuthMappingModel(CamelCaseModel):
    token: str
    chats_count: int
    interactive: bool
    chats_sync: int
    contacts_sync: int
    presence_sync: int
    drafts_sync: int


class ContactMappingModel(CamelCaseModel):
    account_status: int
    country: str
    id: int
    names: list[Any]
    options: list[str]
    phone: int
    updateTime: int

class ProfileMappingModel(CamelCaseModel):
    contact: ContactMappingModel
    profile_options: list[Any]

class MessageLinkMappingModel(CamelCaseModel):
    type: str | None = None
    message: MessageMappingModel | None = None
    message_id: str | None = None


StatusType = Literal['EDITED', 'REPLY', 'USER']

def validate_status(v: Any) -> Any:
    if v not in ('EDITED', 'REPLY', 'USER'):
        return 'USER'
    return v

class MessageMappingModel(CamelCaseModel):
    cid: int = -round(time.time() * 1000)
    attaches: list[Any] = []
    sender: int | None = None
    chat_id: int | None = None
    id: str | None = Field(default=None, serialization_alias='message_id')
    time: int | None = None
    type: str | None = None
    text: str | None = None
    status: Annotated[StatusType, BeforeValidator(validate_status)] = 'USER'
    elements: list[dict[str, Any]] | None = None
    link: MessageLinkMappingModel | None = None


class ReactionInfoModel(CamelCaseModel):
    your_reaction: str | None = None
    total_count: int | None = None
    counters: list[dict[str, Any]] | None = None

MessageLinkMappingModel.model_rebuild()



# structures that are needed in both requests and responses at the same time

class TrackLoginModel(CamelCaseModel):
    track_id: str


# end of structures for responses and requests at the same time