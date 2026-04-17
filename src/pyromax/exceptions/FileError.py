from .BaseMaxApiException import BaseMaxApiException


class FileError(BaseMaxApiException):
    pass


class DownloadFileError(FileError):
    pass