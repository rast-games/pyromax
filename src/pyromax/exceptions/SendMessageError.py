from .BaseMaxApiException import BaseMaxApiException

class SendMessageError(BaseMaxApiException):
    """Raised when sending a message fails."""


class SendMessageFileError(SendMessageError):
    """Raised when message sending fails because of invalid file usage."""


class SendMessageNotFoundError(SendMessageError):
    """Raised when the target chat cannot be found."""