from __future__ import annotations

from typing import Any, TypeVar, Generic, TYPE_CHECKING
from abc import abstractmethod


from ...mixins import AsyncInitializerMixin
from ...encoding import BaseEncoding

if TYPE_CHECKING:
    from ...config import ExtraConfig

ENCODING_TYPE = TypeVar("ENCODING_TYPE", bound=BaseEncoding[Any, Any, Any, Any])


class BaseTransport(AsyncInitializerMixin, Generic[ENCODING_TYPE]):
    # BASE_EXCEPTION_FOR_TRANSPORT: type[Exception]
    #
    # OTHER_EXCEPTIONS_FOR_TRANSPORT: list[type[Exception]]

    @abstractmethod
    async def _async_init(
        self,
        encoding: ENCODING_TYPE,
        extra_config: ExtraConfig,
        *args: Any,
        **kwargs: Any,
    ) -> Any: ...

    @abstractmethod
    def __init__(
        self,
        encoding: ENCODING_TYPE,
        extra_config: ExtraConfig,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
