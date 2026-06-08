from .auth import AuthMixin
from .file import FileMixin
from .user import UserMixin
from .construct import ConstructorMixin
from .message import MessageMixin
from .transport import TransportMixin
from ..payloads.models import BaseFileMappingModel

from ....bases import BaseMapper
from .....protocol import EnvelopeProtocol

class FullMixin( # type: ignore[misc]
    TransportMixin,
    AuthMixin,
    ConstructorMixin,
    MessageMixin,
    UserMixin,
    FileMixin,
    BaseMapper[EnvelopeProtocol, BaseFileMappingModel],
):
    pass