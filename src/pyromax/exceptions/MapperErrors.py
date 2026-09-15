from .BaseMaxApiException import BaseMaxApiException


class BaseMapperError(BaseMaxApiException):
    """Base class for mapper errors."""


class RestartMapperError(BaseMapperError):
    """Raised when the mapper needs to be restarted."""


class NeedReloginMapperError(RestartMapperError):
    pass


class GetQRError(BaseMapperError):
    """Raised when QR code retrieval fails."""


class MapperApiError(BaseMapperError):
    """Raised when the remote API returns an error response."""

    title: str | None = None
    localized_message: str | None = None
    message: str | None = None
    error: str | None = None


class AlreadyFailedError(BaseMapperError):
    """Raised when a send is attempted after mapper failure."""


class MapperCancelledError(MapperApiError):
    """Raised when a send was cancelled."""


class MapperTransportError(BaseMapperError):
    """Raised when a send fails."""


class MapperConnectError(BaseMapperError):
    """Raised when connect fails."""


class MapperLifecycleError(BaseMapperError):
    pass


class MapperRestartCycleError(MapperLifecycleError):
    pass


class MapperNeedReloginLifecycleError(MapperRestartCycleError):
    pass


class MapperNotImplementedError(BaseMapperError, NotImplementedError):
    pass


class MapperNotImplementedMethodError(MapperNotImplementedError):
    pass


class MapperTransportNotSupportedForMethodError(MapperNotImplementedError):
    pass


class ReactionMapperError(MapperApiError):
    """Raised when the operations with reactions fails."""
