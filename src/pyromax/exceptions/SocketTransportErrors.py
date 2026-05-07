from .BaseMaxApiException import BaseMaxApiException


class SocketTransportError(BaseMaxApiException):
    """Base class for socket transport errors."""


class SocketTransportConnectionError(SocketTransportError):
    """Raised when the socket transport connection fails."""


class SocketTransportSendError(SocketTransportError):
    """Raised when the socket transport cannot send data."""