from typing import Literal

from .socket_methods import SocketLoginBuildInMappingMethod
from .websocket_methods import WebSocketLoginBuildInMappingMethod
from .base import BaseBuildInMappingMethod

from ......transport import (
BaseTransport,
WebSocketTransport,
SocketTransportEnvelope
)

LOGIN: dict[type[BaseTransport], type[BaseBuildInMappingMethod]] = {
    WebSocketTransport: WebSocketLoginBuildInMappingMethod,
    SocketTransportEnvelope: SocketLoginBuildInMappingMethod,
}

__translate_name_to_dict: dict[
    str,
    dict[type[BaseTransport], type[BaseBuildInMappingMethod]]
] = {
    'LOGIN': LOGIN,
}


method_names = Literal[
    'LOGIN'
]

def build_method(method_name: method_names, transport: BaseTransport) -> BaseBuildInMappingMethod:
    collection = __translate_name_to_dict.get(method_name, None)
    if collection is None:
        raise RuntimeError(
            f'Try a build not existing method named {method_name}'
        )
    method_class = collection.get(type(transport))
    if method_class is None:
        raise RuntimeError(
            f'Method {method_name} not supported for {transport.__class__.__name__} transport'
        )

    method = method_class()
    return method
