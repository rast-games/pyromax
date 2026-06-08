from ..constants import *
from .payloads.models import WebUserAgentMappingModel, AppUserAgentMappingModel, BaseUserAgentMappingModel
from ....utils import BackoffConfig


DEVICE_TYPE_TO_USERAGENT_MODEL: dict[
    str,
    type[BaseUserAgentMappingModel]
] = {
    'WEB': WebUserAgentMappingModel,
    'DESKTOP': AppUserAgentMappingModel,
}

DEFAULT_BACKOFF_CONFIG = BackoffConfig(min_delay=1.0, max_delay=5.0, factor=1.3, jitter=0.1)

VERSION = 11