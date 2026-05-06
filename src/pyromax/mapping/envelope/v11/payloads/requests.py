from pydantic import Field

from .shared import CamelCaseModel
from .models import BaseUserAgentMappingModel, MessageMappingModel, WebUserAgentMappingModel, AppUserAgentMappingModel

class BaseUserAgentRequest(CamelCaseModel):
    user_agent: BaseUserAgentMappingModel
    device_id: str


class AppUserAgentRequest(BaseUserAgentRequest):
    user_agent: AppUserAgentMappingModel
    device_id: str
    client_session_id: int


class WebUserAgentRequest(CamelCaseModel):
    user_agent: WebUserAgentMappingModel
    device_id: str


class Resolve2FARequest(CamelCaseModel):
    password: str
    track_id: str


class StartPhoneAuthRequest(CamelCaseModel):
    phone: str
    type: str


class VerifySMSCodeRequest(CamelCaseModel):
    verify_code: str
    token: str
    auth_token_type: str


class SendMessageRequest(CamelCaseModel):
    chat_id: int
    message: MessageMappingModel


class KeepAliveRequest(CamelCaseModel):
    interactive: bool = True


# --- Files Requests ---
class CreateCellForFileRequest(CamelCaseModel):
    count: int = 1


class AnyFileRequest(CamelCaseModel):
    type: str = Field(
        serialization_alias='_type'
    )


class FileToPayloadRequest(AnyFileRequest):
    file_id: int


class PhotoToPayloadRequest(AnyFileRequest):
    photo_token: str


class VideoToPayloadRequest(AnyFileRequest):
    video_id: int
    token: str

class GetFileLinkRequest(CamelCaseModel):
    chat_id: int
    message_id: int


class GetContactRequest(CamelCaseModel):
    contact_ids: list[int]

# --- end Files Requests ---



