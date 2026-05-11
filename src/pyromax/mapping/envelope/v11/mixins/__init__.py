from .auth import AuthMixin
from .file import FileMixin
from .user import UserMixin
from .construct import ConstructorMixin
from .message import MessageMixin
from .transport import TransportMixin

from ....bases import BaseMapper
from .....protocol import EnvelopeProtocol

class FullMixin(
    TransportMixin,
    AuthMixin,
    ConstructorMixin,
    MessageMixin,
    UserMixin,
    FileMixin,
    BaseMapper[EnvelopeProtocol],
):
    pass