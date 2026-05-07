from .BaseMaxApiException import BaseMaxApiException


class AnnotationError(BaseMaxApiException):
    """Raised when a handler parameter is not annotated."""