from __future__ import annotations
from typing import TYPE_CHECKING, Any

from ..protocol.registry import PROTOCOLS as _PROTOCOLS
from ..transport.registry import TRANSPORTS as _TRANSPORTS
from ..mapping.registry import MAPPERS as _MAPPERS

if TYPE_CHECKING:
    from ..protocol import BaseMaxProtocol
    from ..transport import BaseTransport
    from ..mapping import BaseMapper

PROTOCOLS: dict[str, type[BaseMaxProtocol[Any, Any]]] = _PROTOCOLS
TRANSPORTS: dict[str, type[BaseTransport]] = _TRANSPORTS
MAPPERS: dict[str, type[BaseMapper[Any]]] = _MAPPERS
