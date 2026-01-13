from enum import Enum

class Opcode(Enum):
    PUSH_NOTIFICATION = 128
    CHAT_INFO = 48
    AUTHORIZE = 19
    GET_CHAT = 48
    TRACK_LOGIN = 289
    METADATA_FOR_LOGIN = 288
    GET_USER_DATA = 291