from .BaseMaxApiException import BaseMaxApiException


class RoutingError(BaseMaxApiException):
    pass


class AlreadyCancelledError(RoutingError):
    """Raised when try a create record after cancelling."""


class RequestWasCancelledError(RoutingError):
    """Exception for default cancelling request."""


class SequenceExhaustedError(RoutingError):
    """Raised when a sequence is exhausted."""
