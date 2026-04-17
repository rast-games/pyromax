from pydantic import Field

from .shared import CamelCaseModel
from .models import UserAgentMappingModel, MessageMappingModel

class UserAgentRequest(CamelCaseModel):
    user_agent: UserAgentMappingModel
    device_id: str


class SendMessageRequest(CamelCaseModel):
    chat_id: int
    message: MessageMappingModel


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


# --- end Files Requests ---



