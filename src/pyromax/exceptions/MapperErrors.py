from .BaseMaxApiException import BaseMaxApiException


class BaseMapperError(BaseMaxApiException):
    """Base class for mapper errors."""


class RestartMapperError(BaseMapperError):
    """Raised when the mapper needs to be restarted."""


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