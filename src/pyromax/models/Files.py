from pydantic import BaseModel


# class BaseFile:
#     data: bytes
#
#     def __init__(self, data: bytes):
#         # super().__init__(**kwargs)
#         self.data = data


class BaseFileAttachment(BaseModel):
    pass


# class Video(BaseFile):
#     pass


class VideoAttachment(BaseFileAttachment):
    pass


# class Photo(BaseFile):
#     pass


class PhotoAttachment(BaseFileAttachment):
    pass


# class File(BaseFile):
#     pass


class FileAttachment(BaseFileAttachment):
    pass