from .BaseMaxApiException import BaseMaxApiException


class SocketTransportError(BaseMaxApiException):
    pass


class SocketTransportConnectionError(SocketTransportError):
    pass


class SocketTransportSendError(SocketTransportError):
    pass