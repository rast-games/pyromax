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
from .CircuitBreakerError import CircuitBreakerOpenError
from .FileError import FileError, DownloadFileError
from .TransportError import (
    BaseTransportError,
    ConnectTransportError,
    ConnectionTransportError,
    SendingTransportError,
    ReceivingTransportError,
    CloseTransportError,
    # SocketTransportError,
    # SocketTransportConnectionError,
    # SocketTransportSendError,
)
from .MapperErrors import (
    BaseMapperError,
    RestartMapperError,
    GetQRError,
    MapperApiError,
    UnsupportedClientVersionMapperError,
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
    AuthInputRequired,
    AttachmentUploadError,
    StopLifecycleError,
    MapperCloseError,
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
from .VersionError import VersionAlreadyExistsError, VersionNotFoundError

__all__ = [
    "BaseMaxApiException",
    "SendMessageError",
    "SendMessageNotFoundError",
    "SendMessageFileError",
    "AnnotationError",
    "BackoffError",
    "CircuitBreakerOpenError",
    "FileError",
    "DownloadFileError",
    "BaseTransportError",
    "SendingTransportError",
    "ConnectTransportError",
    "CloseTransportError",
    "ReceivingTransportError",
    "ConnectionTransportError",
    "RequestWasCancelledError",
    # "SocketTransportError",
    # "SocketTransportConnectionError",
    # "SocketTransportSendError",
    "BaseMapperError",
    "RestartMapperError",
    "GetQRError",
    "MapperApiError",
    "UnsupportedClientVersionMapperError",
    "MapperCancelledError",
    "MapperTransportError",
    "MapperConnectError",
    "MapperCloseError",
    "MapperLifecycleError",
    "StopLifecycleError",
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
    "AttachmentUploadError",
    "AuthInputRequired",
    "VersionAlreadyExistsError",
    "VersionNotFoundError",
]
