from typing import Literal, Any

from .socket_methods import SocketLoginBuildInMappingMethod
from .websocket_methods import WebSocketLoginBuildInMappingMethod
from .base import BaseBuildInMappingMethod
from ......models import DeviceType, BaseDeviceType

from ......transport import BaseTransport, WebSocketTransport, SocketTransport

LOGIN: dict[DeviceType | BaseDeviceType, type[BaseBuildInMappingMethod]] = {
    DeviceType.Web: WebSocketLoginBuildInMappingMethod,
    DeviceType.Android: SocketLoginBuildInMappingMethod,
    DeviceType.Desktop: SocketLoginBuildInMappingMethod,
}

__translate_name_to_dict: dict[
    str, dict[DeviceType | BaseDeviceType, type[BaseBuildInMappingMethod]]
] = {
    "LOGIN": LOGIN,
}


method_names = Literal["LOGIN"]


def build_method(
    method_name: method_names,
    device_type: DeviceType | BaseDeviceType,
    # transport: BaseTransport[Any],
) -> BaseBuildInMappingMethod:
    """Build method.

    :param method_name: method_names instance to process.
    :type method_name: method_names
    :returns: The resulting BaseBuildInMappingMethod value.
    :rtype: BaseBuildInMappingMethod
    :raises RuntimeError: If the requested action cannot be completed.
    """
    collection = __translate_name_to_dict.get(method_name, None)
    if collection is None:
        raise RuntimeError(f"Try a build not existing method named {method_name}")
    method_class = collection.get(device_type)
    if method_class is None:
        raise RuntimeError(
            f"Method {method_name} not supported for {device_type} device type"
        )

    method = method_class()
    return method
