from __future__ import annotations
from typing import TYPE_CHECKING, Any, cast


from ..mixins import AsyncConstructorType

from ..protocol.registry import PROTOCOLS as _PROTOCOLS
from ..transport.registry import TRANSPORTS as _TRANSPORTS
from ..mapping.registry import MAPPERS as _MAPPERS

from ..protocol import BaseMaxProtocol
from ..transport import BaseTransport
from ..mapping import BaseMapper


PROTOCOLS = cast(dict[str, AsyncConstructorType[BaseMaxProtocol[Any, Any]]], _PROTOCOLS)
TRANSPORTS = cast(dict[str, AsyncConstructorType[BaseTransport]], _TRANSPORTS)
MAPPERS = cast(dict[str, AsyncConstructorType[BaseMapper[Any, Any]]], _MAPPERS)