from ...payloads.models import PhotoMappingModel, VideoMappingModel, FileMappingModel
from ..ToDTO.FileTranslate import PhotoMapping, VideoMapping, FileMapping

FILE_TYPES = {
    PhotoMappingModel: PhotoMapping,
    VideoMappingModel: VideoMapping,
    FileMappingModel: FileMapping
}