from abc import abstractmethod
from collections.abc import AsyncGenerator

from src.pyromax.mixins import AsyncInitializerMixin
from src.pyromax.models import BaseFileAttachment
from src.pyromax.models import BaseMaxObject
from src.pyromax.protocol.bases.request_response import Response, Request


class BaseMapper(AsyncInitializerMixin):
    @abstractmethod
    async def initialize_client(self, **kwargs): pass


    @abstractmethod
    async def listen_updates(self) -> AsyncGenerator[BaseMaxObject | Request, None]: pass


    @abstractmethod
    async def upload_file(self, data: bytes, typeof: type[BaseFileAttachment]) -> BaseFileAttachment: pass


    @abstractmethod
    async def send_message(self, chat_id: int, text: str, attaches: list[BaseFileAttachment]): pass