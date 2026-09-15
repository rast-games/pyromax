from .BaseMaxApiException import BaseMaxApiException
from .SendMessageError import (
    SendMessageFileError,
    SendMessageNotFoundError,
    SendMessageError,
)
from .ReactionError import (
    ReactionError,
)
from .AnnotationError import AnnotationError
from .BackoffError import BackoffError
from .FileError import FileError, DownloadFileError
from .TransportError import (
    BaseTransportError,
    ConnectTransportError,
    ConnectionTransportError,
    SendingTransportError,
    # SocketTransportError,
    # SocketTransportConnectionError,
    # SocketTransportSendError,
)
from .MapperErrors import (
    BaseMapperError,
    RestartMapperError,
    GetQRError,
    MapperApiError,
    AlreadyFailedError,
    MapperCancelledError,
    MapperTransportError,
    MapperConnectError,
    MapperLifecycleError,
    MapperNotImplementedError,
    MapperNotImplementedMethodError,
    MapperTransportNotSupportedForMethodError,
    ReactionMapperError,
    MapperRestartCycleError,
    MapperNeedReloginLifecycleError,
    NeedReloginMapperError,
)
from .RoutingErrors import AlreadyCancelledError, RoutingError, RequestWasCancelledError
from .ProtocolErrors import (
    BaseProtocolError,
    ReceiveProtocolError,
    SendingProtocolError,
    ConnectProtocolError,
    CloseProtocolError,
    GetUpdatesProtocolError,
)
from .fsm import DataNotDictLikeError
from .ParseError import ParseMaxApiError
from .MethodError import BaseMaxApiMethodError

__all__ = [
    "BaseMaxApiException",
    "SendMessageError",
    "SendMessageNotFoundError",
    "SendMessageFileError",
    "AnnotationError",
    "BackoffError",
    "FileError",
    "DownloadFileError",
    "BaseTransportError",
    "SendingTransportError",
    "ConnectTransportError",
    "ConnectionTransportError",
    "RequestWasCancelledError",
    # "SocketTransportError",
    # "SocketTransportConnectionError",
    # "SocketTransportSendError",
    "BaseMapperError",
    "RestartMapperError",
    "GetQRError",
    "MapperApiError",
    "MapperCancelledError",
    "MapperTransportError",
    "MapperConnectError",
    "MapperLifecycleError",
    "AlreadyFailedError",
    "AlreadyCancelledError",
    "ReactionMapperError",
    "RoutingError",
    "RequestWasCancelledError",
    "BaseProtocolError",
    "ReceiveProtocolError",
    "SendingProtocolError",
    "ConnectProtocolError",
    "CloseProtocolError",
    "GetUpdatesProtocolError",
    "DataNotDictLikeError",
    "MapperNotImplementedError",
    "MapperNotImplementedMethodError",
    "MapperTransportNotSupportedForMethodError",
    "ParseMaxApiError",
    "ReactionError",
    "BaseMaxApiMethodError",
    "MapperRestartCycleError",
    "MapperNeedReloginLifecycleError",
    "NeedReloginMapperError",
]
