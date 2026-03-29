from __future__ import annotations
from abc import abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from typing_extensions import TYPE_CHECKING

from src.pyromax.mixins import AsyncInitializerMixin

if TYPE_CHECKING:
    from src.pyromax.models import BaseFileAttachment
    from src.pyromax.models import BaseMaxObject
    from src.pyromax.protocol import Request
    from src.pyromax import MaxApi, BaseMaxProtocol


class BaseMapper(AsyncInitializerMixin):

    @abstractmethod
    async def _async_init(self, max_api: MaxApi, protocol: BaseMaxProtocol, *args, **kwargs): pass

    @abstractmethod
    async def initialize_client(self, **kwargs): pass


    @abstractmethod
    async def listen_updates(self, context: Any) -> AsyncGenerator[BaseMaxObject | Request, None]: pass


    @abstractmethod
    async def upload_file(self, data: bytes, typeof: type[BaseFileAttachment]) -> BaseFileAttachment: pass


    @abstractmethod
    async def send_message(self, chat_id: int, text: str, attaches: list[BaseFileAttachment], **kwargs): pass