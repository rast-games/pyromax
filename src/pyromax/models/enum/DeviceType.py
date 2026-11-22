from enum import StrEnum


class BaseDeviceType(StrEnum):
    pass


class DeviceType(BaseDeviceType):
    Web = "WEB"
    Desktop = "DESKTOP"
    Android = "ANDROID"
