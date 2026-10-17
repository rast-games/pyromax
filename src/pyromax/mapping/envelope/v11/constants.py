from ...bases.MappingConstants import MappingConstants
from ..constants import Cmd as Cmd, Opcode as Opcode
from .payloads.models import (
    WebUserAgentMappingModel,
    AppUserAgentMappingModel,
    BaseUserAgentMappingModel,
    MobileUserAgentMappingModel,
)
from ....utils import BackoffConfig

DEVICE_TYPE_TO_USERAGENT_MODEL: dict[str, type[BaseUserAgentMappingModel]] = {
    "WEB": WebUserAgentMappingModel,
    "DESKTOP": AppUserAgentMappingModel,
    "ANDROID": MobileUserAgentMappingModel,
    "IOS": MobileUserAgentMappingModel,
}

DEFAULT_BACKOFF_CONFIG = BackoffConfig(
    min_delay=1.0, max_delay=5.0, factor=1.3, jitter=0.1
)

VERSION = 11


class ErrorCode(MappingConstants):
    """Error codes emitted by the Envelope V11 API."""

    UNSUPPORTED_CLIENT_VERSION = "client.unsupported-version"
    LOGIN_TOKEN = "login.token"
    LOGIN_CREDENTIALS = "login.cred"
    VERIFY_CODE_WRONG = "verify.code.wrong"
    LIMIT_VIOLATED = "error.limit.violate"
    CODE_ATTEMPT_LIMIT = "error.code.attempt.limit"
    AUTH_REQUEST_FORBIDDEN = "auth.request.forbidden"
    ATTACHMENT_NOT_READY = "attachment.not.ready"
    PROTOCOL_PAYLOAD = "proto.payload"
    NOT_FOUND = "not.found"
    UNKNOWN_REACTION = "error.message.like.unknown.reaction"
