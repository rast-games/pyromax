from typing import Any, ClassVar

from typing_extensions import Self

from .shared import CamelCaseModel
from pydantic import Field, AliasPath, model_validator, AliasChoices
from .models import (ProfileMappingModel, MessageMappingModel, ReactionInfoMappingModel, ContactMappingModel, PasswordConfig)


class TokenAttrsResponse(CamelCaseModel):
    token: str = Field(validation_alias=AliasPath('LOGIN', 'token'))


class SuccessLoginResponse(CamelCaseModel):
    token_attrs: TokenAttrsResponse
    profile: ProfileMappingModel
    TwoFactor: ClassVar[bool] = False


class StartSMSAuthResponse(CamelCaseModel):
    alt_action_duration: int
    code_length: int
    request_count_left: int
    request_max_duration: int
    token: str


class PasswordChallengeResponse(CamelCaseModel):
    config: PasswordConfig
    track_id: str
    email: str


class TwoFactorLoginResponse(CamelCaseModel):
    password_challenge: PasswordChallengeResponse
    token_attrs: dict
    TwoFactor: ClassVar[bool] = True

class ChoiceLoginVariantResponse(CamelCaseModel):
    payload: SuccessLoginResponse | TwoFactorLoginResponse

class AuthResponse(CamelCaseModel):
    chats: list[Any]
    config: dict[Any, Any]
    contacts: list[Any]
    messages: dict[Any, Any]
    presence: dict[Any, Any]
    profile: ProfileMappingModel
    time: int
    token: str | None = None


class SendMessageResponse(CamelCaseModel):
    chat_id: int | None = None
    mark: int | None = None
    message: MessageMappingModel


class ErrorMessageResponse(CamelCaseModel):
    error: str | None = None
    error_message: str | None = Field(default=None, alias='message')
    localized_message: str | None = None
    title: str | None = None


class TrackStatusResponse(CamelCaseModel):
    expires_at: int | float
    login_available: bool = False

    @model_validator(mode='after')
    def validate_after(self, v: Any) -> Self:
        self.expires_at /= 1000
        return self


class TrackLoginResponse(ErrorMessageResponse):
    status: TrackStatusResponse | None = None


class MetadataResponse(CamelCaseModel):
    polling_interval: int | float
    qr_link: str
    ttl: int
    track_id: str
    expires_at: int | float

    @model_validator(mode='after')
    def validate_after(self, v: Any) -> Self:
        self.polling_interval /= 1000
        self.expires_at /= 1000
        return self


class ResponseWithUrl(CamelCaseModel):
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


class GetContactResponse(CamelCaseModel):
    contacts: list[ContactMappingModel]

# --- Updates ---

class PushUpdateResponse(CamelCaseModel):
    chat_id: int
    message: MessageMappingModel
    ttl: bool
    mark: int
    unread: int | None
    prev_message_id: str | int | None = None


class EmojiReactionUpdateResponse(CamelCaseModel):
    chat_id: int
    message_id: str
    reaction_info: ReactionInfoMappingModel


