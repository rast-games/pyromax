from __future__ import annotations
from typing import Generic, TypeVar, TYPE_CHECKING, Any

from pydantic import ConfigDict

from .base import BaseMaxObject

if TYPE_CHECKING:
    from ..mapping import BaseMapper
    from ..protocol import BaseMaxProtocol
    from ..transport import BaseTransport

    M = TypeVar("M", bound=BaseMapper[Any, Any])
    P = TypeVar("P", bound=BaseMaxProtocol[Any, Any])
    T = TypeVar("T", bound=BaseTransport[Any])
else:
    M = TypeVar("M")
    P = TypeVar("P")
    T = TypeVar("T")


class AuthFlow(BaseMaxObject, Generic[M, P, T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    token: str | None = None
    # max_api: MaxApi
    mapper: M
    protocol: P
    transport: T
