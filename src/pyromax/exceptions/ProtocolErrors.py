from .BaseMaxApiException import BaseMaxApiException


class BaseProtocolError(BaseMaxApiException):
    pass


class SendingProtocolError(BaseProtocolError):
    pass


class ReceiveProtocolError(BaseProtocolError):
    pass

class ConnectProtocolError(BaseProtocolError):
    pass