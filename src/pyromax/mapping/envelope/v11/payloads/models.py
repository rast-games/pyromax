from __future__ import annotations

from abc import abstractmethod, ABC
from typing import Annotated, Literal, Any

from pydantic import Field, BeforeValidator, AliasChoices, AliasPath

from .....models import BaseFileAttachment, PhotoAttachment, VideoAttachment, FileAttachment
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


class NameMappingModel(CamelCaseModel):
    name: str = ''
    first_name: str = ''
    last_name: str = ''
    type: str = ''

class ContactMappingModel(CamelCaseModel):
    account_status: int
    country: str | None = None
    description: str = ''
    email: str | None = None
    id: int
    names: list[NameMappingModel]
    options: list[str]
    phone: int | None = None
    photo_id: int | None = None
    update_time: int
    registration_time: int
    base_url: str | None = None

class ProfileMappingModel(CamelCaseModel):
    contact: ContactMappingModel
    profile_options: list[Any]


class BaseFileMappingModel(BaseFileAttachment, CamelCaseModel, ABC):
    message_id: str | None = None
    uploaded: bool = False
    chat_id: int | None = None
    type: str = Field(serialization_alias='_type', validation_alias=AliasChoices(
        AliasPath('type'),
        AliasPath('_type')
    ))


    @property
    @abstractmethod
    def get_payload_to_get_link(self) -> dict[str, Any] | None:
        return {
            'messageId': self.message_id,
            'chatId': self.chat_id,
        }

    @property
    @abstractmethod
    def to_payload(self) -> list[dict[str, Any]]: pass


class PhotoMappingModel(BaseFileMappingModel, PhotoAttachment):
    photo_token: str
    photo_id: int | str | None = None
    base_url: str | None = None
    height: int | None = None
    width: int | None = None
    preview_data: Any | None = None



    # never will be called
    @property
    def get_payload_to_get_link(self) -> dict[str, Any] | None: return None


    @property
    def to_payload(self) -> list[dict[str, Any]]:
        from .requests import PhotoToPayloadRequest
        photos = []
        photos.append(
            PhotoToPayloadRequest(
                type='PHOTO',
                photo_token=self.photo_token
            ).model_dump(by_alias=True)
        )
        return photos

class VideoMappingModel(BaseFileMappingModel, VideoAttachment):
    token: str
    video_id: int
    video_type: int | None = None
    duration: int | None = None
    height: int | None = None
    width: int | None = None
    preview_data: Any | None = None
    trumbnail: str | None = None


    @property
    def to_payload(self) -> list[dict[str, Any]]:
        from .requests import VideoToPayloadRequest
        return [
            VideoToPayloadRequest(
                type='VIDEO',
                video_id=self.video_id,
                token=self.token
            ).model_dump(by_alias=True),
        ]


    @property
    def get_payload_to_get_link(self) -> dict[str, Any] | None:
        res = super().get_payload_to_get_link
        if res is None:
            raise RuntimeError('get_payload_to_get_link should return dict')
        res.update(
            {
                'videoId': self.video_id,
                'token': self.token,
            }
        )

        return res


class FileMappingModel(BaseFileMappingModel, FileAttachment):
    token: str | None = None
    file_id: int
    size: int | None = None
    name: str | None = None


    @property
    def to_payload(self) -> list[dict[str, Any]]:
        from .requests import FileToPayloadRequest

        return [
            FileToPayloadRequest(
                type='FILE',
                file_id=self.file_id,
            ).model_dump(by_alias=True),
        ]

    @property
    def get_payload_to_get_link(self) -> dict[str, Any] | None:
        res = super().get_payload_to_get_link
        if res is None:
            raise RuntimeError('get_payload_to_get_link should return dict')
        res.update(
            {
                'fileId': self.file_id,
            }
        )

        return res



class MessageLinkMappingModel(CamelCaseModel):
    type: str | None = None
    message: MessageMappingModel | None = None
    message_id: str | None = None


StatusType = Literal['EDITED', 'REPLY', 'USER', 'REMOVED']

def validate_status(v: Any) -> Any:
    if v not in ('EDITED', 'REPLY', 'USER', 'REMOVED'):
        return 'USER'
    return v

class MessageMappingModel(CamelCaseModel):
    cid: int = -round(time.time() * 1000)
    attaches: list[VideoMappingModel | PhotoMappingModel | FileMappingModel] = []
    sender: int | None = None
    chat_id: int | None = None
    id: str | None = Field(default=None, serialization_alias='message_id')
    time: int | None = None
    type: str | None = None
    text: str | None = None
    status: Annotated[StatusType, BeforeValidator(validate_status)] = 'USER'
    elements: list[dict[str, Any]] | None = None
    link: MessageLinkMappingModel | None = None


class ReactionInfoMappingModel(CamelCaseModel):
    your_reaction: str | None = None
    total_count: int | None = None
    counters: list[dict[str, Any]] | None = None

MessageLinkMappingModel.model_rebuild()




# structures that are needed in both requests and responses at the same time

class TrackLoginModel(CamelCaseModel):
    track_id: str


# end of structures for responses and requests at the same time