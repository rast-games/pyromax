from .BaseMaxApiException import BaseMaxApiException

class LoggingError(BaseMaxApiException):
    """Exception raised when a logging error occurs."""


class LoggingTimeoutError(BaseMaxApiException):
    """Exception raised when a logging timeout occurs."""
