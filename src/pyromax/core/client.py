from __future__ import annotations
import asyncio
import logging
from typing import Any, TYPE_CHECKING, AsyncGenerator
from collections.abc import Sequence, Callable

from ..mixins import AsyncInitializerMixin
from ..methods import SendMessageMethod
from ..exceptions import SendMessageError

if TYPE_CHECKING:
    from ..dispatcher.event import Update, MaxObject
    from ..protocol import Response
    from ..methods import BaseMaxApiMethod
    from ..models import BaseFileAttachment, MessageLink

from .context import *



if TYPE_CHECKING:
    from ..protocol import BaseMaxProtocol
    from ..transport import BaseTransport
    from ..mapping import BaseMapper
    from ..models import Contact


class MaxApi(AsyncInitializerMixin):
    """Asynchronous client for MAX Messenger.

    The client initializes a transport, protocol, and mapper from the
    project registry. Initialization is asynchronous and requires the
    selected backend names to be available in the corresponding registries.

    Raises
    ------
    RuntimeError
        If a transport, protocol, or mapper name is not supported.
    """

    async def _async_init(
            self,
            device_type: str = 'WEB',
            password: str | None = None,
            token: str | None = None,
            transport: str = 'websocket',
            protocol: str = 'EnvelopeProtocol',
            mapper: str = 'EnvelopeV11',
            transport_options: dict[str, Any] | None = None,
            workflow_data: dict[Any, Any] | None = None,
            **kwargs: Any
    ) -> None:
        if workflow_data is None:
            workflow_data = {}


        """Asynchronously initialize transport, protocol, and mapper.

        Parameters
        ----------
        device_type
            Device type reported to the API.
        password
            Optional account password.
        token
            Optional auth token.
        transport
            Transport backend name.
        protocol
            Protocol backend name.
        mapper
            Mapper backend name.
        transport_options
            Keyword arguments passed to the transport constructor.
        kwargs
            Extra keyword arguments passed to mapper initialization.
        """

        logger = logging.getLogger('MaxApi')

        if transport not in TRANSPORTS:
            raise RuntimeError(f"transport {transport} is not supported")

        if protocol not in PROTOCOLS:
            raise RuntimeError(f"protocol {protocol} is not supported")

        if mapper not in MAPPERS:
            raise RuntimeError(f"mapper {mapper} is not supported")



        logger.info('Start initialization...')
        logger.info('Initializing transport...')
        if transport_options:
            max_transport = await TRANSPORTS[transport](**transport_options)
        else:
            max_transport = await TRANSPORTS[transport]()
        logger.info('Transport initialized.')
        logger.info('Initializing protocol...')
        protocol_res: Any = await PROTOCOLS[protocol](transport=max_transport)
        max_protocol: BaseMaxProtocol[Any, Any] = protocol_res

        # max_protocol: BaseMaxProtocol[Any, Any] = await PROTOCOLS[protocol](transport=max_transport) # type: ignore
        logger.info('Protocol initialized.')
        logger.info('Initializing mapper...')
        max_mapper = await MAPPERS[mapper](self, protocol=max_protocol)
        logger.info('Mapper initialized.')
        await asyncio.to_thread(
            self.__init__, # type: ignore[misc]
            protocol=max_protocol,
            password=password,
            transport=max_transport,
            mapper=max_mapper,
            transport_options=transport_options,
            token=token,
            logger=logger,
            workflow_data=workflow_data,
            device_type=device_type,
        )

        await self.mapper.initialize_client(
            token=token,
            device_type=device_type,
            password=password,
            **kwargs
        )


    def __init__(
            self,
            device_type: str = 'WEB',
            password: str | None = None,
            transport: str | BaseTransport | None = None,
            protocol: str | BaseMaxProtocol[Any, Any] | None = None,
            mapper: BaseMapper[Any, Any] | None = None,
            transport_options: dict[str, Any] | None = None,
            token: str | None = None,
            logger: logging.Logger | None = None,
            workflow_data: dict[Any, Any] | None = None,
            **kwargs: Any

    ) -> None:

        if workflow_data is None:
            workflow_data = {}

        if logger is None:
            logger = logging.getLogger('MaxApi')

        if transport is None or protocol is None or mapper is None:
            raise RuntimeError('transport or protocol or mapper cannot be None')

        self.transport = transport
        self.transport_options = transport_options
        self.protocol = protocol
        self.mapper = mapper
        self.token = token
        self.id: int | None = None
        self.phone: str | None = None
        self.names: Any | list[dict[str, Any]] | None = None
        self.__logger: logging.Logger | None = logger
        self.workflow_data = workflow_data



    async def __call__(
            self,
            class_of_method: type[BaseMaxApiMethod[Any]],
            *args: Any,
            **kwargs: Any
    ) -> Any:
        if self.__logger is None:
            raise RuntimeError('Try a call method before initialization, because logger has not been initialized')
        self.__logger.debug('Calling MaxApi method: %s', class_of_method.__name__)
        method = class_of_method().as_(self)

        return await method(
            *args,
            **kwargs
        )


    def listen_updates(self, context: Any) -> tuple[Callable[[Response], MaxObject], AsyncGenerator[Response, None]]:
        """Yield incoming updates forever.

        Parameters
        ----------
        context
            Runtime context passed to the mapper.

        Returns
        -------
        AsyncGenerator[Update, None]
            Stream of incoming updates.
        """
        return self.mapper.listen_updates(context=context)


    async def send_message(
            self,
            chat_id: int,
            text: str = '',
            attaches: list[BaseFileAttachment] | None = None,
            link: MessageLink | None = None,
    ) -> Any:
        """Send a message to a chat.

                Parameters
                ----------
                chat_id
                    Target chat identifier.
                text
                    Message text.
                attaches
                    Optional list of attachments.
                link
                    Optional message link object.

                Returns
                -------
                Any
                    API response returned by the mapper.

                Raises
                ------
                SendMessageError
                    If message sending fails.
                """
        try:
            return await self(
                SendMessageMethod,
                text=text,
                chat_id=chat_id,
                attaches=attaches,
                link=link,
            )
        except SendMessageError as e:
            if self.__logger is None:
                raise AttributeError('logger not initialized in MaxApi instance')
            self.__logger.warning('Failed to send message: %s', e)
            raise e


    async def download_file(
            self,
            file: BaseFileAttachment
    ) -> tuple[bytes, dict[str, str]] | tuple[None, None]:
        return await self.mapper.download_file(file)


    async def get_member_by_id(self, member_id: int) -> Sequence[Contact | Any]:
        return await self.mapper.get_member_by_id(member_id)