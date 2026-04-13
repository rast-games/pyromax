from __future__ import annotations
import asyncio
import logging
from typing import Any, TYPE_CHECKING


from ..mixins import AsyncInitializerMixin
from ..methods import SendMessageMethod

if TYPE_CHECKING:
    from ..methods import BaseMaxApiMethod
    from .. import BaseFileAttachment, MessageLink

from .context import *


if TYPE_CHECKING:
    from ..protocol import BaseMaxProtocol
    from ..transport import BaseTransport
    from ..mapping import BaseMapper



class MaxApi(AsyncInitializerMixin):
    async def _async_init(
            self,
            token: str | None = None,
            transport: str = 'Websocket',
            protocol: str = 'EnvelopeProtocol',
            mapper: str = 'EnvelopeV11',
            transport_options: dict[str, Any] | None = None,
            **kwargs: Any
    ) -> None:

        logger = logging.getLogger('MaxApi')

        if not transport_options:
            transport_options = {'url': "wss://ws-api.oneme.ru/websocket"}

        if transport not in TRANSPORTS:
            raise RuntimeError(f"transport {transport} is not supported")

        if protocol not in PROTOCOLS:
            raise RuntimeError(f"protocol {protocol} is not supported")

        if mapper not in MAPPERS:
            raise RuntimeError(f"mapper {mapper} is not supported")



        logger.info('Start initialization...')
        logger.info('Initializing transport...')
        max_transport = await TRANSPORTS[transport](**transport_options)
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
            transport=max_transport,
            mapper=max_mapper,
            transport_options=transport_options,
            token=token,
            logger=logger
        )


        await self.mapper.initialize_client(
            token=token,
            **kwargs
        )


    def __init__(
            self,
            transport: BaseTransport | None = None,
            protocol: BaseMaxProtocol[Any, Any] | None = None,
            mapper: BaseMapper[Any] | None = None,
            transport_options: dict[str, Any] | None = None,
            token: str | None = None,
            logger: logging.Logger | None = None,
            # device_id: str = get_random_device_id(),
            # protocol_version='v11',
            # device_type: str = 'WEB',
            # timezone: str = 'Europe/Moscow',
            # screen: str = '1440x2560 1.0x',
            # locale: str = 'ru',
            # device_locale: str = 'ru',
            # os_version: str = 'Linux',
            # app_version: str = '26.2.10',
            # header_user_agent: str = 'Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0',
            # device_name: str = 'Firefox',
            # chats_count: int = 40,
            # interactive: bool = True,
            # presence_sync: int = -1,
            # chats_sync: int = 0,
            # contacts_sync: int = 0,
            # drafts_sync: int = 0,
    ) -> None:

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
        self.names: list[dict[str, Any]] | None = None
        self.__logger: logging.Logger | None = logger



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


    async def send_message(
            self,
            chat_id: int,
            text: str = '',
            attaches: list[BaseFileAttachment] | None = None,
            link: MessageLink | None = None,
    ) -> Any:
        return await self(
            SendMessageMethod,
            text=text,
            chat_id=chat_id,
            attaches=attaches,
            link=link,
        )