from __future__ import annotations
import asyncio
import logging
from typing import Any, TYPE_CHECKING

from ..mixins import AsyncInitializerMixin

if TYPE_CHECKING:
    from ..methods import BaseMaxApiMethod

from .context import *




class MaxApi(AsyncInitializerMixin):
    async def _async_init(
            self,
            token: str = None,
            transport: str = 'Websocket',
            transport_options: dict = None,
            protocol: str = 'EnvelopeProtocol',
            mapper: str = 'EnvelopeV11',
            **kwargs
    ):

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
        transport = await TRANSPORTS[transport](**transport_options)
        logger.info('Transport initialized.')
        logger.info('Initializing protocol...')
        protocol = await PROTOCOLS[protocol](transport=transport)
        logger.info('Protocol initialized.')
        logger.info('Initializing mapper...')
        max_mapper = await MAPPERS[mapper](self, protocol=protocol)
        logger.info('Mapper initialized.')

        await asyncio.to_thread(
            self.__init__,
            protocol=protocol,
            transport=transport,
            transport_options=transport_options,
            mapper=max_mapper,
            token=token,
            logger=logger
        )

        await self.mapper.initialize_client(
            token=token,
            **kwargs
        )


    def __init__(
            self,
            transport: BaseTransport,
            protocol: BaseMaxProtocol,
            transport_options: dict,
            mapper: BaseMapper,
            token: str | None = None,
            logger: logging.Logger = None,
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
    ):

        if logger is None:
            logger = logging.getLogger('MaxApi')

        self.transport = transport
        self.transport_options = transport_options
        self.protocol = protocol
        self.mapper = mapper
        self.token = token
        self.id: int | None = None
        self.phone: str | None = None
        self.names: list[dict] | None = None
        self.__logger: logging.Logger | None = logger



    async def __call__(
            self,
            class_of_method: type[BaseMaxApiMethod],
            *args,
            **kwargs
    ) -> Any:

        self.__logger.debug('Calling MaxApi method: %s', class_of_method.__name__)
        method = class_of_method().as_(self)

        return await method(
            *args,
            **kwargs
        )
