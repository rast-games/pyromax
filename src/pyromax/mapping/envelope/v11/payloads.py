from typing import Literal, Optional, Annotated, Any
import time


from pydantic import BaseModel, ConfigDict, Field, AliasChoices, AliasPath, BeforeValidator, model_validator


def to_camel_case(snake_str):
    words = snake_str.split('_')
    camel_case = [words[0].lower()] + [word.capitalize() for word in words[1:]]
    return ''.join(camel_case)


CAMEL_CASE_CONFIG = ConfigDict(
        alias_generator=to_camel_case,
        validate_by_name=True
    )


class CamelCaseModel(BaseModel):
    model_config = CAMEL_CASE_CONFIG


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

class ContactModel(CamelCaseModel):
    account_status: int
    country: str
    id: int
    names: list
    options: list[str]
    phone: int
    updateTime: int

class ProfileModel(CamelCaseModel):
    contact: ContactModel
    profile_options: list


class TokenAttrsModel(CamelCaseModel):
    token: str = Field(validation_alias=AliasPath('LOGIN', 'token'))

class SuccessLoginModel(CamelCaseModel):
    token_attrs: TokenAttrsModel
    profile: ProfileModel

class AuthResponseModel(CamelCaseModel):
    chats: list
    config: dict
    contacts: list
    messages: dict
    presence: dict
    profile: ProfileModel
    time: int
    token: str | None = None

class MessageLinkModel(CamelCaseModel):
    type: str | None = None
    message: Optional['MessageModel'] = None
    message_id: str | None = None


StatusType = Literal['EDITED', 'REPLY', 'USER']


def validate_status(v: Any) -> str:
    if v not in ('EDITED', 'REPLY', 'USER'):
        return 'USER'
    return v


class ErrorMessageModel(CamelCaseModel):
    error: str = None
    error_message: str = Field(default=None, alias='message')
    localized_message: str = None


class TrackLoginPayloadModel(CamelCaseModel):
    track_id: str

class TrackStatusModel(CamelCaseModel):
    expires_at: int
    login_available: bool = False

    @model_validator(mode='after')
    def validate_after(self, v):
        self.expires_at /= 1000
        return self

class TrackLoginResponseModel(ErrorMessageModel):
    status: TrackStatusModel | None = None

class MetadataPayloadModel(CamelCaseModel):
    polling_interval: int
    qr_link: str
    ttl: int
    track_id: str
    expires_at: int

    @model_validator(mode='after')
    def validate_after(self, v):
        self.polling_interval /= 1000
        self.expires_at /= 1000
        return self

class MessageModel(CamelCaseModel):
    cid: int = -round(time.time() * 1000)
    attaches: list = []
    sender: int | None = None
    chat_id: int | None = None
    id: str | None = Field(default=None, serialization_alias='message_id')
    time: int | None = None
    type: str | None = None
    text: str | None = None
    status: Annotated[StatusType, BeforeValidator(validate_status)] = 'USER'
    elements: list[dict] | None = None
    link: MessageLinkModel | None = None


MessageLinkModel.model_rebuild()


class SendMessageModel(CamelCaseModel):
    chat_id: int
    message: MessageModel


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


class PayloadWithUrlModel(CamelCaseModel):
    upload_url: str = Field(
        validation_alias=AliasChoices(
            AliasPath('url'),
            AliasPath('info', 0, 'url')
        )
    )
    token: str | None = Field(
        validation_alias=AliasPath('info', 0, 'token'),
        default=None
    )
    file_id: int | None = Field(
        validation_alias=AliasPath('info', 0, 'fileId'),
        default=None
    )
    video_id: int | None = Field(
        validation_alias=AliasPath('info', 0, 'videoId'),
        default=None
    )


class AnyFileToPayloadModel(CamelCaseModel):
    type: str = Field(
        serialization_alias='_type'
    )


class FileToPayloadModel(AnyFileToPayloadModel):
    file_id: int


class PhotoToPayloadModel(AnyFileToPayloadModel):
    photo_token: str


class VideoToPayloadModel(AnyFileToPayloadModel):
    video_id: int
    token: str