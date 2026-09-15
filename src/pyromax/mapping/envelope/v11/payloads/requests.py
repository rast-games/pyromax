import time
from random import randint
from typing import Any, Literal

from pydantic import Field

from .shared import CamelCaseModel, PollFlagsMappingModel, PollAnswerMappingModel
from .models import (
    BaseUserAgentMappingModel,
    MessageMappingModel,
    WebUserAgentMappingModel,
    AppUserAgentMappingModel,
    MobileUserAgentMappingModel,
    VideoMappingModel,
    PhotoMappingModel,
    FileMappingModel,
    ShareMappingModel,
    CreateGroupMessageMappingModel,
    ChangeGroupSettingsMappingModel,
    TwoFactorActionMappingModel,
    ChangeProfileSettingsMappingModel,
    TelemetryEventMappingModel,
)


class BaseUserAgentRequest(CamelCaseModel):
    user_agent: BaseUserAgentMappingModel
    device_id: str


class AppUserAgentRequest(BaseUserAgentRequest):
    user_agent: AppUserAgentMappingModel
    device_id: str
    client_session_id: int = Field(default_factory=lambda: randint(1, 70))


class WebUserAgentRequest(BaseUserAgentRequest):
    user_agent: WebUserAgentMappingModel
    device_id: str


class MobileUserAgentRequest(AppUserAgentRequest):
    user_agent: MobileUserAgentMappingModel
    mt_instance_id: str = Field(..., alias="mt_instanceid")


class Resolve2FARequest(CamelCaseModel):
    password: str
    track_id: str


class StartPhoneAuthRequest(CamelCaseModel):
    phone: str
    type: str
    mode: bytes | None


class VerifySMSCodeRequest(CamelCaseModel):
    verify_code: str
    token: str
    auth_token_type: str


class ConfirmRegistrationRequest(CamelCaseModel):
    first_name: str
    last_name: str | None = None
    token: str
    token_type: str = "REGISTER"


class GetEmailCodeRequest(CamelCaseModel):
    track_id: str
    email: str


class SetHintRequest(CamelCaseModel):
    track_id: str
    hint: str


class VerifyEmailRequest(CamelCaseModel):
    track_id: str
    verify_code: str


class SetPasswordRequest(CamelCaseModel):
    track_id: str
    password: str


class GetTrackIdFor2FARequest(CamelCaseModel):
    type: int = 0


class SetTwoFactorRequest(CamelCaseModel):
    expected_capabilities: list[int]
    track_id: str
    password: str
    hint: str | None = None


class RemoveTwoFactorRequest(CamelCaseModel):
    track_id: str
    expected_capabilities: list[int] = Field(
        default_factory=lambda: [TwoFactorActionMappingModel.REMOVE_2FA.value]
    )
    remove2fa: bool = Field(default=True, alias="remove2fa")


class ApproveQrLoginRequest(CamelCaseModel):
    qr_link: str


class TelemetryRequest(CamelCaseModel):
    events: list[TelemetryEventMappingModel]


class SendMessageRequest(CamelCaseModel):
    chat_id: int
    message: MessageMappingModel
    notify: bool = True


class EditMessageRequest(CamelCaseModel):
    chat_id: int
    message_id: str | int
    text: str | None = None
    elements: list[dict[str, Any]] | None = None
    attachments: list[
        VideoMappingModel
        | PhotoMappingModel
        | FileMappingModel
        | ShareMappingModel
        | Any
    ] = []


class GetMessagesRequest(CamelCaseModel):
    chat_id: int
    message_ids: list[int | str]


class GetChatHistoryRequest(CamelCaseModel):
    chat_id: int
    forward: int
    backward: int = 40
    backward_time: int = 0
    forward_time: int = 0
    get_chat: bool = False
    from_: int = Field(serialization_alias="from")
    item_type: Literal["DELAYED", "REGULAR"] = "REGULAR"
    get_messages: bool = True
    interactive: bool = False


class DeleteMessageRequest(CamelCaseModel):
    chat_id: int
    message_ids: list[str | int]
    for_me: bool = False


class PinMessageRequest(CamelCaseModel):
    chat_id: int
    notify_pin: bool = True
    pin_message_id: str | int


class ReactionInfoRequest(CamelCaseModel):
    reaction_type: str = "EMOJI"
    id: str


class AddReactionRequest(CamelCaseModel):
    chat_id: int
    message_id: str | int
    reaction: ReactionInfoRequest


class RemoveReactionRequest(CamelCaseModel):
    chat_id: int
    message_id: str | int


class GetReactionsRequest(CamelCaseModel):
    chat_id: int
    message_ids: list[int] | list[str]


class ReadMessageRequest(CamelCaseModel):
    chat_id: int
    message_id: str | int
    type: Literal["READ_MESSAGE", "READ_REACTION"] = "READ_MESSAGE"
    mark: int = Field(default_factory=lambda: int(time.time() * 1000))


class VotePollRequest(CamelCaseModel):
    chat_id: int
    message_id: int | str
    poll_id: int
    answers_ids: list[int]


class CreateChatRequest(CamelCaseModel):
    message: CreateGroupMessageMappingModel
    notify: bool = True


class ChatMemberOperationRequest(CamelCaseModel):
    chat_id: int
    user_ids: list[int]
    operation: Literal["add", "remove"] = "add"
    show_history: bool | None = None
    clean_msg_period: int | None = None


class ChangeGroupSettingsRequest(CamelCaseModel):
    chat_id: int
    options: ChangeGroupSettingsMappingModel


class ChangeGroupProfileRequest(CamelCaseModel):
    chat_id: int
    theme: str | None = None
    description: str | None = None


class LinkGroupRequest(CamelCaseModel):
    link: str


class RevokePrivateLinkRequest(CamelCaseModel):
    revoke_private_link: bool = True
    chat_id: int


class GetChatInfoRequest(CamelCaseModel):
    chat_ids: list[int]


class LeaveChatRequest(CamelCaseModel):
    chat_id: int


class FetchChatsRequest(CamelCaseModel):
    marker: int


class FetchJoinRequestsRequest(CamelCaseModel):
    chat_id: int
    count: int = 100
    type: str = "JOIN_REQUEST"


class JoinRequestActionRequest(CamelCaseModel):
    chat_id: int
    user_ids: list[int]
    type: str = "JOIN_REQUEST"
    show_history: bool | None = True
    operation: Literal["add", "remove"]


class DeleteChatRequest(CamelCaseModel):
    chat_id: int
    last_event_time: int
    for_all: bool = True


class AddAdminRequest(CamelCaseModel):
    chat_id: int
    user_ids: list[int]
    type: Literal["ADMIN"] = "ADMIN"
    operation: str = "add"
    permissions: int


class KeepAliveRequest(CamelCaseModel):
    interactive: bool = True


class SearchByPhoneRequest(CamelCaseModel):
    phone: str


class ContactRequest(CamelCaseModel):
    first_name: str
    last_name: str | None = None


class ContactActionRequest(CamelCaseModel):
    action: Literal["ADD", "REMOVE"]
    contact_id: int


class ImportContactsRequest(CamelCaseModel):
    contact_list: dict[str, ContactRequest]  # phone -> contact payload


# --- Files Requests ---
class CreateCellForFileRequest(CamelCaseModel):
    count: int = 1
    type: int = 0
    uploader_type: int = 0


class CreateCellForProfilePhotoRequest(CreateCellForFileRequest):
    profile: bool = False


class ChangeProfileRequest(CamelCaseModel):
    first_name: str
    last_name: str | None = None
    description: str | None = None
    photo_token: str | None = None
    avatar_type: Literal["USER_AVATAR"] = "USER_AVATAR"


class CreateFolderRequest(CamelCaseModel):
    id: str
    title: str
    include: list[int]
    filters: list[Any]


class GetFoldersRequest(CamelCaseModel):
    folder_sync: int = 0


class UpdateFolderRequest(CamelCaseModel):
    id: str
    title: str
    include: list[int]
    filters: list[Any]
    options: list[Any]


class DeleteFoldersRequest(CamelCaseModel):
    folder_ids: list[str]


class ChangeProfileSettingsRequest(CamelCaseModel):
    settings: ChangeProfileSettingsMappingModel


class AnyFileRequest(CamelCaseModel):
    type: str = Field(serialization_alias="_type")


class FileToPayloadRequest(AnyFileRequest):
    file_id: int


class PhotoToPayloadRequest(AnyFileRequest):
    photo_token: str


class VideoToPayloadRequest(AnyFileRequest):
    video_id: int
    token: str


class PollToPayloadRequest(AnyFileRequest):
    title: str
    answers: list[PollAnswerMappingModel]
    settings: int


class GetFileLinkRequest(CamelCaseModel):
    chat_id: int
    message_id: int


class GetContactRequest(CamelCaseModel):
    contact_ids: list[int]


# --- end Files Requests ---
