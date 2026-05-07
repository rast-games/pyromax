from .BaseMaxApiException import BaseMaxApiException


class FileError(BaseMaxApiException):
    """Base class for file-related errors."""


class DownloadFileError(FileError):
    """Raised when a file download fails."""