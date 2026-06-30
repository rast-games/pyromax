from __future__ import annotations
from abc import abstractmethod, ABC
import random
from typing import Annotated, Literal, Any, ClassVar, TYPE_CHECKING

from pydantic import Field, BeforeValidator, AliasChoices, AliasPath, model_validator

from .....models import BaseFileAttachment, PhotoAttachment, VideoAttachment, FileAttachment, ShareAttachment, BaseUserAgent
from .shared import CamelCaseModel
from .....utils import get_random_device_id_numeric, get_random_device_id, get_random_app_version_and_build_number
from .....config import WEB_APP_VERSION, WEB_SCREEN, DEFAULT_WEB_HEADER_USER_AGENT

if TYPE_CHECKING:
    from .requests import BaseUserAgentRequest, AppUserAgentRequest, WebUserAgentRequest

import time

class BaseUserAgentMappingModel(BaseUserAgent, CamelCaseModel, ABC):
    device_type: str
    locale: str = 'ru'
    device_id: str = get_random_device_id()
    timezone: str = 'Europe/Moscow'
    device_locale: str = 'ru'
    os_version: str = 'Windows 10 Version 22H2'
    device_name: str = 'WINDOWS10'


    @abstractmethod
    def to_request(self) -> BaseUserAgentRequest: ...


class WebUserAgentMappingModel(BaseUserAgentMappingModel):
    device_type: str = 'WEB'
    device_id: str = Field(default=get_random_device_id(), exclude=True)
    header_user_agent: str = DEFAULT_WEB_HEADER_USER_AGENT
    app_version: str = WEB_APP_VERSION
    screen: str = WEB_SCREEN


    def to_request(self) -> WebUserAgentRequest:
        device_id = self.device_id
        from .requests import WebUserAgentRequest
        return WebUserAgentRequest(device_id=device_id, user_agent=self)


class AppUserAgentMappingModel(BaseUserAgentMappingModel):
    device_type: str = 'DESKTOP'
    screen: str = '2.0x'
    device_id: str = Field(default_factory=get_random_device_id_numeric, exclude=True)
    client_session_id: int = Field(default_factory=lambda: random.randint(1, 30), exclude=True)
    build_number: int
    app_version: str

    @model_validator(mode='before')
    @classmethod
    def set_random_version_pair(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if 'build_number' in data and 'app_version' not in data or 'app_version' in data and 'build_number' not in data:
                raise ValueError('you need give pair from build_number and app_version')

            if 'build_number' not in data and 'app_version' not in data:
                app_ver, build_num = get_random_app_version_and_build_number()
                data['build_number'] = build_num
                data['app_version'] = app_ver
        return data

    def to_request(self) -> AppUserAgentRequest:
        client_session_id = self.client_session_id
        device_id = self.device_id
        from .requests import AppUserAgentRequest
        return AppUserAgentRequest(device_id=device_id, client_session_id=client_session_id, user_agent=self)


class AuthMappingModel(CamelCaseModel):
    token: str
    chats_count: int
    interactive: bool
    chats_sync: int
    contacts_sync: int
    presence_sync: int
    drafts_sync: int


class PasswordConfig(CamelCaseModel):
    pass_max_len: int
    pass_min_len: int
    hint_max_len: int

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
    base_raw_url: str | None = None

class ProfileMappingModel(CamelCaseModel):
    contact: ContactMappingModel
    profile_options: list[Any]


class BaseFileMappingModel(BaseFileAttachment, CamelCaseModel, ABC):
    is_attach: ClassVar[bool] = True
    is_downloadable: ClassVar[bool] = True
    message_id: str | None = None
    uploaded: bool = Field(default=False, exclude=True)
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



class ShareMappingModel(BaseFileMappingModel, ShareAttachment):
    image: PhotoMappingModel | None = None
    description: str | None = None
    contentLevel: bool | None = None
    share_id: int
    title: str | None = None
    url: str | None = None
    is_downloadable: ClassVar[bool] = False

    @property
    def to_payload(self) -> list[dict[str, Any]]:
        return []


    @property
    def get_payload_to_get_link(self) -> dict[str, Any] | None:
        raise TypeError('Try a download Share attachment')

class MessageLinkMappingModel(CamelCaseModel):
    type: str | None = None
    message: MessageMappingModel | None = None
    message_id: int | None = None


StatusType = Literal['EDITED', 'REPLY', 'USER', 'REMOVED']

def validate_status(v: Any) -> Any:
    if v not in ('EDITED', 'REPLY', 'USER', 'REMOVED'):
        return 'USER'
    return v


class MessageMappingModel(CamelCaseModel):
    cid: int = -round(time.time() * 1000)
    attaches: list[VideoMappingModel | PhotoMappingModel | FileMappingModel | ShareMappingModel | Any] = []
    sender: int | None = None
    chat_id: int | None = None
    id: str | int | None = Field(default=None, serialization_alias='message_id')
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

class TrackLoginMappingModel(CamelCaseModel):
    track_id: str

# end of structures for responses and requests at the same time