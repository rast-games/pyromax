from __future__ import annotations

from abc import abstractmethod
from collections.abc import Awaitable, Iterable
from typing import Any, TYPE_CHECKING, Generic
from typing_extensions import TypeVar

from ...mixins import AsyncInitializerMixin
from .request_response import Request, Response

if TYPE_CHECKING:
    from .methods import BaseMaxProtocolMethod
    from ...transport import BaseTransport
    from ...encoding import BaseEncoding
    from ...config import ExtraConfig

T = TypeVar("T", bound=Request[Any], contravariant=True)
R = TypeVar("R", bound=Response, covariant=True)

TRANSPORT_TYPE = TypeVar("TRANSPORT_TYPE", bound="BaseTransport[Any]", default=Any)


class BaseMaxProtocol(AsyncInitializerMixin, Generic[T, R, TRANSPORT_TYPE]):

    @abstractmethod
    async def _async_init(
        self,
        transport: TRANSPORT_TYPE,
        encoding: BaseEncoding[Any, Any, Any, Any],
        extra_config: ExtraConfig,
        *args: Any,
        **kwargs: Any,
    ) -> Any: ...

    @abstractmethod
    def __init__(
        self,
        transport: BaseTransport[Any],
        encoding: BaseEncoding[Any, Any, Any, Any],
        extra_config: ExtraConfig,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...

    @abstractmethod
    async def send(
        self, method: BaseMaxProtocolMethod[T], data: Any | None = None
    ) -> Awaitable[R]:
        """Send.

        :param method: BaseMaxProtocolMethod[T] instance to process.
        :type method: BaseMaxProtocolMethod[T]
        :param data: Contextual data passed through the processing pipeline.
        :type data: Any | None
        :returns: The resulting Awaitable[R] value.
        :rtype: Awaitable[R]
        """
        pass

    @abstractmethod
    async def get_updates(self) -> Iterable[Any]:
        """Retrieve updates.

        :returns: The resulting collection.
        :rtype: Iterable[Any]
        """
        pass

    @property
    @abstractmethod
    def transport(self) -> BaseTransport[Any]:
        """Transport.

        :returns: The resulting BaseTransport value.
        :rtype: BaseTransport
        """
        pass
