from __future__ import annotations
from abc import abstractmethod
from collections.abc import AsyncGenerator, Sequence
from typing import Any, Generic, TypeVar, TYPE_CHECKING

from ...mixins import AsyncInitializerMixin


if TYPE_CHECKING:
    from ...models import BaseFileAttachment, BaseMaxObject
    from ...protocol import Request
    from ...dispatcher.event import Update
    from ...core import MaxApi
    from ...protocol import BaseMaxProtocol


T_protocol = TypeVar('T_protocol', bound='BaseMaxProtocol[Any, Any]')
# attaches_type = TypeVar('attaches_type', bound=BaseFileAttachment)


class BaseMapper(AsyncInitializerMixin, Generic[T_protocol]):

    protocol: T_protocol

    @abstractmethod
    async def _async_init(self, max_api: MaxApi, protocol: T_protocol, *args: Any, **kwargs: Any) -> None: pass

    @abstractmethod
    async def initialize_client(self, **kwargs: Any) -> None: pass


    @abstractmethod
    def listen_updates(self, context: Any) -> AsyncGenerator[Update, None]: pass


    @abstractmethod
    async def upload_file(self, data: bytes | None, typeof: type[BaseFileAttachment], **kwargs: Any) -> Any: pass


    @abstractmethod
    async def send_message(self, chat_id: int, text: str | None = None, attaches: Sequence[Any] | None = None, **kwargs: Any) -> Any | None: pass