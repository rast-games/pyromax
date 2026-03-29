from ..bases.MappingConstants import MappingConstants



class Opcode(MappingConstants):
    PING = 1
    SEND_USER_AGENT = 6
    AUTHORIZE = 19
    # CHAT_INFO = 48
    GET_CHAT = 48
    GET_CHAT_MESSAGES_PER_CHUNK = 49
    SEND_MESSAGE = 64
    CREATE_PHOTO = 80
    CREATE_VIDEO = 82
    GET_VIDEO = 83
    GET_FILE = 88
    CREATE_FILE = 87
    PUSH_NOTIFICATION = 128
    MESSAGE_REACTION_UPDATE = 156
    METADATA_FOR_LOGIN = 288
    TRACK_LOGIN = 289
    GET_USER_DATA = 291



class Cmd(MappingConstants):
    REQUEST = 0
    RESPONSE = 1