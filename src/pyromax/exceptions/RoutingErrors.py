from .BaseMaxApiException import BaseMaxApiException

class RoutingError(BaseMaxApiException):
    pass


class AlreadyCancelledError(RoutingError):
    """Raised when try a create record after cancelling."""