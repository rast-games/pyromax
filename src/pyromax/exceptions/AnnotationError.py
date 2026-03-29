from .BaseMaxApiException import BaseMaxApiException


class AnnotationError(BaseMaxApiException):
    """Exception raised when param in handler not annotated"""