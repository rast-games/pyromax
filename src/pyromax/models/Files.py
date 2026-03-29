from pydantic import BaseModel

class BaseFileAttachment(BaseModel):
    pass


class VideoAttachment(BaseFileAttachment):
    pass


class PhotoAttachment(BaseFileAttachment):
    pass


class FileAttachment(BaseFileAttachment):
    pass