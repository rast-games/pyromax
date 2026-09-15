from typing import Any, ClassVar, Literal

from typing_extensions import Self

from pydantic import Field, AliasPath, model_validator, AliasChoices

from .....models import SyncState
from .shared import CamelCaseModel
from .models import (
    ProfileMappingModel,
    MessageMappingModel,
    ReactionInfoMappingModel,
    ContactMappingModel,
    PasswordConfig,
    CreateGroupMessageMappingModel,
    ChatMappingModel,
    SessionMappingModel,
    PollStateMappingModel,
    AuthConfigMappingModel,
)


class UserAgentResponse(CamelCaseModel):
    calls_seed: int | None = None


class TokenAttrsResponse(CamelCaseModel):
    token: str | None = Field(
        default=None, validation_alias=AliasPath("LOGIN", "token")
    )
    register_token: str | None = Field(
        default=None, validation_alias=AliasPath("REGISTER", "token")
    )


class SuccessLoginResponse(CamelCaseModel):
    token_attrs: TokenAttrsResponse
    profile: ProfileMappingModel | None = None
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
    email: str | None = None


class TwoFactorLoginResponse(CamelCaseModel):
    password_challenge: PasswordChallengeResponse
    token_attrs: TokenAttrsResponse
    TwoFactor: ClassVar[bool] = True


class ChoiceLoginVariantResponse(CamelCaseModel):
    payload: SuccessLoginResponse | TwoFactorLoginResponse


class AuthResponse(CamelCaseModel):
    chats: list[ChatMappingModel]
    # config: dict[Any, Any] | None = None
    contacts: list[ContactMappingModel | None] = Field(default_factory=list)
    messages: dict[int, list[MessageMappingModel]] = Field(default_factory=dict)
    presence: dict[Any, Any] | None = None
    profile: ProfileMappingModel | None = None
    time: int | None = None
    token: str | None = None
    config: AuthConfigMappingModel | None = None

    def update_sync_state(self, current: SyncState) -> SyncState:
        sync_time = self.time
        config_hash = self.config.hash if self.config is not None else None

        return SyncState(
            chats_sync=(sync_time if sync_time is not None else current.chats_sync),
            contacts_sync=(
                sync_time if sync_time is not None else current.contacts_sync
            ),
            drafts_sync=(sync_time if sync_time is not None else current.drafts_sync),
            presence_sync=(
                sync_time if sync_time is not None else current.presence_sync
            ),
            config_hash=(
                config_hash if config_hash is not None else current.config_hash
            ),
        )


class ConfirmRegistrationResponse(CamelCaseModel):

    user_token: int
    profile: ProfileMappingModel
    token_type: Literal[
        "START_AUTH",
        "CHECK_CODE",
        "REGISTER",
        "RESEND",
    ]
    token: str


class GetTrackIdFor2FAResponse(CamelCaseModel):
    track_id: str | None = None


class ProfileContainsResponse(CamelCaseModel):
    profile: ProfileMappingModel


class ConfigHashContainsResponse(CamelCaseModel):
    config_hash: str | None = None


class SendMessageResponse(CamelCaseModel):
    chat_id: int | None = None
    mark: int | None = None
    message: MessageMappingModel


class EditMessageResponse(CamelCaseModel):
    message: MessageMappingModel


class GetChatHistoryMessagesResponse(CamelCaseModel):
    messages: list[MessageMappingModel]
    chat: ChatMappingModel | None = None


class GetChatHistoryMessagesIdsResponse(CamelCaseModel):
    message_ids: list[str | int]
    chat: ChatMappingModel | None = None


class GetChatHistoryResponse(CamelCaseModel):
    payload: GetChatHistoryMessagesResponse | GetChatHistoryMessagesIdsResponse


class GetMessagesResponse(GetChatHistoryMessagesResponse):
    chat_id: int


class AddOrRemoveReactionResponse(CamelCaseModel):
    reaction_info: ReactionInfoMappingModel | None = None


class GetReactionsResponse(CamelCaseModel):
    messages_reactions: dict[str | int, ReactionInfoMappingModel]


class CreateGroupResponse(CamelCaseModel):
    chat_id: int | None = None
    mark: int
    message: MessageMappingModel
    chat: ChatMappingModel | None = None


class ChatContainsResponse(CamelCaseModel):
    chat: ChatMappingModel | None = None


class MessageContainsResponse(CamelCaseModel):
    message: MessageMappingModel | None = None


class ChatsContainsResponse(CamelCaseModel):
    chats: list[ChatMappingModel] | None = None


class MembersContainsResponse(CamelCaseModel):
    members: list[ContactMappingModel] | None = None


class VoteStateContainsResponse(CamelCaseModel):
    state: PollStateMappingModel | None = None


class ErrorMessageResponse(CamelCaseModel):
    error: str | None = None
    error_message: str | None = Field(default=None, alias="message")
    localized_message: str | None = None
    title: str | None = None


class TrackStatusResponse(CamelCaseModel):
    expires_at: int | float
    login_available: bool = False

    @model_validator(mode="after")
    def validate_after(self, v: Any) -> Self:
        """Validate and normalize validate after.

        :param v: The v value.
        :type v: Any
        :returns: The current instance.
        :rtype: Self
        """
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

    @model_validator(mode="after")
    def validate_after(self, v: Any) -> Self:
        """Validate and normalize validate after.

        :param v: The v value.
        :type v: Any
        :returns: The current instance.
        :rtype: Self
        """
        self.polling_interval /= 1000
        self.expires_at /= 1000
        return self


class ResponseWithUrl(CamelCaseModel):
    upload_url: str = Field(
        validation_alias=AliasChoices(AliasPath("url"), AliasPath("info", 0, "url"))
    )
    token: str | None = Field(
        validation_alias=AliasPath("info", 0, "token"), default=None
    )
    file_id: int | None = Field(
        validation_alias=AliasPath("info", 0, "fileId"), default=None
    )
    video_id: int | None = Field(
        validation_alias=AliasPath("info", 0, "videoId"), default=None
    )


class CloseAllSessionsResponse(CamelCaseModel):
    token: str | None = None


class GetContactResponse(CamelCaseModel):
    contacts: list[ContactMappingModel]


class ContactContainsResponse(CamelCaseModel):
    contact: ContactMappingModel


class ContactsContainsResponse(CamelCaseModel):
    contacts: list[ContactMappingModel]


class SessionsContainsResponse(CamelCaseModel):
    sessions: list[SessionMappingModel]


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
    message_id: str | int
    reaction_info: ReactionInfoMappingModel
