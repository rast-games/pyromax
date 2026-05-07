from .BaseMaxApiException import BaseMaxApiException

class BackoffError(BaseMaxApiException):
    """Raised when the client cannot recover after backoff."""