from enum import StrEnum


class BaseRegistry(StrEnum):
    pass


class UserRegistry(BaseRegistry):
    pass


class TransportRegistry(BaseRegistry):
    WebSocketTransport = "Websocket"
    SocketTransport = "Socket"


class EncodingRegistry(BaseRegistry):
    NoEncoding = "NoEncoding"
    MsgPackDictEncoding = "MsgPackDictEncoding"
    JsonEncoding = "JsonEncoding"


class ProtocolRegistry(BaseRegistry):
    EnvelopeProtocol = "EnvelopeProtocol"


class MapperRegistry(BaseRegistry):
    EnvelopeV11Mapper = "EnvelopeV11"
