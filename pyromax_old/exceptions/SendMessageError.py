from .BaseMaxApiException import BaseMaxApiException

class SendMessageError(BaseMaxApiException):
    """Exception raised when a sending message fails."""



class SendMessageFileError(SendMessageError):
    """Exception raised when a sending message fails because the message with the attached file contained a text or/and other attachments."""


class SendMessageNotFoundError(SendMessageError):
    """Exception raised when a sending message fails because the chat not found"""