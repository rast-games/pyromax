from .BaseMaxApiException import BaseMaxApiException


class AnnotationHandlerError(BaseMaxApiException):
    """Exception raised when param in handler not annotated"""