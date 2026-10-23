import abc
from typing import Any, ClassVar, Generic, TYPE_CHECKING

from typing_extensions import TypeVar

from ......protocol import Envelope, BaseMaxProtocolMethod
from ....constants import Opcode, Cmd
from ...constants import VERSION
from ......exceptions import BaseMapperError

if TYPE_CHECKING:
    from ...Mapper import Mapper
    from .....bases import BaseMapper

    MapperType = TypeVar("MapperType", default=Mapper, bound=BaseMapper[Any, Any])
else:
    MapperType = TypeVar("MapperType")


class BaseMethod(abc.ABC, Generic[MapperType], BaseMaxProtocolMethod[Envelope]):
    # Transport failures do not contain an API response, so breaker recovery
    # cycles are enabled by default and can be disabled for a specific method.
    circuit_breaker_transport_retry_enabled: ClassVar[bool] = True

    # API failures are explicit responses. Retrying them is opt-in because a
    # rejected mutating operation is not necessarily safe to replay.
    circuit_breaker_retry_safe: ClassVar[bool] = False

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the base method.

        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        """
        self.args = kwargs

    @abc.abstractmethod
    async def __call__(self, request: Envelope) -> Envelope:
        """Populate an envelope for the base protocol request.

        :param request: Protocol request envelope to populate or send.
        :type request: Envelope
        :returns: The envelope populated with the request opcode and payload.
        :rtype: Envelope
        """
        pass

    _mapper: MapperType | None = None

    @property
    def mapper(self) -> MapperType:
        if self._mapper is None:
            raise BaseMapperError("Immutable mapper method not bound to mapper")
        return self._mapper

    @mapper.setter
    def mapper(self, mapper: MapperType) -> None:
        if self._mapper is not None:
            raise BaseMapperError("Immutable mapper method already bound to mapper")
        self._mapper = mapper

    @property
    def is_bound(self) -> bool:
        return True if self._mapper is not None else False

    @property
    def VERSION(self) -> int:
        return self.mapper.VERSION


__all__ = [
    "BaseMethod",
    "Opcode",
    "Cmd",
    "VERSION",
    "Envelope",
]
