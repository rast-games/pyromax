from enum import StrEnum
from typing import TypeAlias


class BaseDeviceType(StrEnum):
    """Base enum for application-defined device types."""


class DeviceType(BaseDeviceType):
    Web = "WEB"
    Desktop = "DESKTOP"
    Android = "ANDROID"


DeviceTypeLike: TypeAlias = DeviceType | BaseDeviceType
