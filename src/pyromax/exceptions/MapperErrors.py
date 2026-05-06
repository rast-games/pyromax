from .BaseMaxApiException import BaseMaxApiException


class BaseMapperError(BaseMaxApiException):
    pass


class RestartMapperError(BaseMapperError):
    pass


class GetQRError(BaseMapperError):
    pass

class MapperApiError(BaseMapperError):
    title: str | None = None
    localized_message: str | None = None
    message: str | None = None
    error: str | None = None


class AlreadyFailedError(BaseMapperError):
    """Raising when you try a send when mapper already failed"""