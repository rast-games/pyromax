from .BaseMaxApiException import BaseMaxApiException


class BaseTransportError(BaseMaxApiException):
    """Base exception class for TransportError"""


class ConnectTransportError(BaseTransportError):
    """Raised when if connect fails"""


class ReceivingTransportError(BaseTransportError):
    """Raised when receive fails"""


class CloseTransportError(BaseTransportError):
    """Raised when close fails"""


class ConnectionTransportError(BaseTransportError):
    """Raised when connect fails"""


class SendingTransportError(BaseTransportError):
    """Raised when send fails"""


# ------


# class SocketTransportError(BaseTransportError):
#     """Base class for socket transport errors."""
#
#
# class SocketTransportConnectionError(SocketTransportError, ConnectionTransportError):
#     """Raised when the socket transport connection fails."""
#
#
# class SocketTransportConnectError(SocketTransportError, ConnectTransportError):
#     """Raised when the socket transport connect fails."""
#
#
# class SocketTransportSendError(SocketTransportError, SendingTransportError):
#     """Raised when the socket transport cannot send data."""
