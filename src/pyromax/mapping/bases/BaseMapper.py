from __future__ import annotations
from abc import abstractmethod
from collections.abc import AsyncGenerator, Sequence, Mapping, Callable
from typing import Any, Generic, TypeVar, TYPE_CHECKING

from pydantic import BaseModel


from ...protocol import Response
from ...mixins import AsyncInitializerMixin, AsyncConstructorMeta

if TYPE_CHECKING:
    # from ...models import BaseFileAttachment, BaseMaxObject, Message, Contact
    from ...models.Message import Message
    from ...models.Contact import Contact
    from ...models import BaseMaxObject, BaseFileAttachment
    from ...protocol import Request
    from ...dispatcher.event import Update
    from ...core import MaxApi
    from ...protocol import BaseMaxProtocol
    from ...methods import BaseMaxApiMethod
    from ...config import ExtraConfig


T_protocol = TypeVar("T_protocol", bound="BaseMaxProtocol[Any, Any]")
T_file = TypeVar("T_file", bound="BaseFileAttachment")
# attaches_type = TypeVar('attaches_type', bound=BaseFileAttachment)


class BaseMapper(AsyncInitializerMixin, Generic[T_protocol, T_file]):

    protocol: T_protocol

    @property
    @abstractmethod
    def DEVICE_TYPE_TO_USERAGENT_MODEL(self) -> Mapping[str, type[BaseModel]]:
        """D e v i c e t y p e t o u s e r a g e n t m o d e l.

        :returns: The resulting Mapping[str, type[BaseModel]] value.
        :rtype: Mapping[str, type[BaseModel]]
        """
        pass

    @abstractmethod
    async def _async_init(
        self,
        max_api: MaxApi,
        protocol: T_protocol,
        extra_config: ExtraConfig,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Async init.

        :param max_api: MAX client to bind or use.
        :type max_api: MaxApi
        :param protocol: Protocol backend or protocol instance.
        :type protocol: T_protocol
        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        """
        pass

    @abstractmethod
    async def start(self, *args: Any, **kwargs: Any) -> None:
        """Initialize client.

        :param device_type: The device type value.
        :type device_type: str
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def start_auth_flow(self, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    async def end_auth_flow(
        self, token: str | None, *args: Any, **kwargs: Any
    ) -> Any: ...

    @abstractmethod
    def listen_updates(
        self, context: Any
    ) -> tuple[
        Callable[[Response], Response | BaseMaxObject], AsyncGenerator[Response, None]
    ]:
        """Listen for updates.

        :param context: Runtime context used while processing the request.
        :type context: Any
        :returns: Items produced by the iterator.
        :rtype: tuple[Callable[[Response], Response | BaseMaxObject], AsyncGenerator[Response, None]]
        """
        pass

    @abstractmethod
    async def upload_file(
        self, data: bytes | None, typeof: type[T_file], **kwargs: Any
    ) -> list[T_file]:
        """Upload file.

        :param data: Contextual data passed through the processing pipeline.
        :type data: bytes | None
        :param typeof: Attachment class that determines the upload type.
        :type typeof: type[T_file]
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting collection.
        :rtype: list[T_file]
        """
        pass

    @abstractmethod
    async def download_file(
        self, file: T_file, **kwargs: Any
    ) -> tuple[bytes, dict[str, str]] | tuple[None, None]:
        """Download file.

        :param file: File attachment to process.
        :type file: T_file
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting tuple[bytes, dict[str, str]] | tuple[None, None] value.
        :rtype: tuple[bytes, dict[str, str]] | tuple[None, None]
        """
        pass

    @abstractmethod
    async def send_message(
        self,
        chat_id: int,
        text: str | None = None,
        attaches: Sequence[Any] | None = None,
        **kwargs: Any,
    ) -> Message | None:
        """Send message.

        :param chat_id: Identifier of the chat.
        :type chat_id: int
        :param text: Message or textual content.
        :type text: str | None
        :param attaches: Attachments associated with the message.
        :type attaches: Sequence[Any] | None
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting Message | None value.
        :rtype: Message | None
        """
        pass

    @abstractmethod
    async def get_members_by_ids(self, member_ids: list[int]) -> Sequence[Contact]:
        """Retrieve members by ids.

        :param member_ids: Identifiers of the members.
        :type member_ids: list[int]
        :returns: The resulting collection.
        :rtype: Sequence[Contact]
        """
        pass

    @abstractmethod
    async def call_method(
        self, method: type[BaseMaxApiMethod[Any]], *args: Any, **kwargs: Any
    ) -> Any:
        """Call a high layer method in mapper

        :param method: High layer method to call
        :type method: type[BaseMaxApiMethod[Any]]

        :returns: High layer domain model as a rule
        :rtype: Any

        :raises MapperNotImplementedMethodError: if mapper not support this method
        :raises MapperTransportNotSupportedForMethodError: if mapper not support this method for chosen transport

        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        """
