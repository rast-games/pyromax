import asyncio
import logging
from asyncio import Task, Lock
from collections.abc import AsyncGenerator

from src.pyromax.mapping.bases.BaseMapper import BaseMapper
from src.pyromax.models import BaseMaxObject, BaseFileAttachment, BaseFile
from src.pyromax.protocol.bases.base import BaseMaxProtocol
from src.pyromax.protocol.envelope import Envelope, EnvelopeProtocol
from src.pyromax.utils.debug_tasks import debug_tasks
from src.pyromax.utils.get_random_string import get_random_device_id
from .methods import SendUserAgentMethod, SendAuthTokenMethod, SendKeepAlivePingMethod, GetUrlToUploadFileMethod
from .payloads import UserAgentPayload, UserAgentModel
from .translate import translate


class Mapper(BaseMapper):

    def __init__(
            self,
            protocol: EnvelopeProtocol,
            keepalive_ping_interval: int
    ):
        self.protocol = protocol
        self._keepalive_ping_interval = keepalive_ping_interval
        self.__logger = logging.getLogger('MapperV11')
        self._keepalive_task: None  | Task = None
        self._update_listener_task: None | Task = None
        self.token = None
        self._manage_lifecycle_task: None | Task = None
        self._update_listener_lock: Lock = Lock()


    async def _async_init(
            self,
            protocol: EnvelopeProtocol,
            keepalive_ping_interval: int = 30,
    ):

        if not isinstance(protocol, BaseMaxProtocol):
            raise TypeError("protocol must be an instance of BaseMaxProtocol")


        await asyncio.to_thread(self.__init__, protocol=protocol, keepalive_ping_interval=keepalive_ping_interval)

        await self.connect()

        self._manage_lifecycle_task = asyncio.create_task(self._manage_lifecycle())



        self.__logger.info("Mapper initialized")


    # async def _propagate_update(
    #         self,
    # ):
    #
    #     update_generator = self.listen_updates()
    #
    #
    #     async for update in update_generator:
    #         print(f"New update received: {update}")




    async def _send_user_agent(
            self,
            device_id: str,
            device_type: str,
            timezone: str,
            screen: str,
            locale: str,
            device_locale: str,
            os_version: str,
            app_version: str,
            header_user_agent: str,
            device_name: str,
    ) -> None:
        await self.protocol.send(method=SendUserAgentMethod(
            device_id=device_id,
            user_agent=UserAgentModel(
                device_type=device_type,
                timezone=timezone,
                screen=screen,
                locale=locale,
                device_locale=device_locale,
                os_version=os_version,
                app_version=app_version,
                header_user_agent=header_user_agent,
                device_name=device_name,
            )
        ), data={})


    async def listen_updates(
            self,
    ) -> AsyncGenerator[BaseMaxObject, None]:

        """Endless updates reader"""

        async with self._update_listener_lock:
            while True:
                updates = await self.protocol.get_updates()

                for update in updates:
                    yield translate(update)


    async def _send_auth_token(
            self,
            token: str,
            chats_count: int,
            interactive: bool,
            presence_sync: int,
            chats_sync: int,
            contacts_sync: int,
            drafts_sync: int
    ) -> None:

        await self.protocol.send(method=SendAuthTokenMethod(
            token=token,
            chats_count=chats_count,
            interactive=interactive,
            presence_sync=presence_sync,
            chats_sync=chats_sync,
            contacts_sync=contacts_sync,
            drafts_sync=drafts_sync,
        ), data={})


    async def _manage_lifecycle(
            self,
    ):
        while True:
            # debug_tasks()
            await self.protocol.failed.wait()
            await self.close()
            await self.connect()
            await self._login(
                token = self.token
            )



    async def connect(
            self,
    ):

        await self.protocol.connect()
        if self._keepalive_task:
            self._keepalive_task.cancel()

        # if self._update_listener_task:
        #     self._update_listener_task.cancel()


        self._keepalive_task = asyncio.create_task(self._keepalive())
        # self._update_listener_task = asyncio.create_task(self._propagate_update())


    async def close(
            self,
    ):
        await self.protocol.close()

        if self._keepalive_task:
            self._keepalive_task.cancel()


        # if self._update_listener_task:
        #     self._update_listener_task.cancel()


    async def initialize_client(
            self,
            token: str,
            device_id: str = get_random_device_id(),
            protocol_version='v11',
            device_type: str = 'WEB',
            timezone: str = 'Europe/Moscow',
            screen: str = '1440x2560 1.0x',
            locale: str = 'ru',
            device_locale: str = 'ru',
            os_version: str = 'Linux',
            app_version: str = '26.2.10',
            header_user_agent: str = 'Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0',
            device_name: str = 'Firefox',
            chats_count: int = 40,
            interactive: bool = True,
            presence_sync: int = -1,
            chats_sync: int = 0,
            contacts_sync: int = 0,
            drafts_sync: int = 0,
    ):

        self.token = token


        # await self.connect()

        # self._keepalive_task = asyncio.create_task(self._keepalive())

        await self._login(
            token = token,
            device_id = device_id,
            device_type = device_type,
            timezone = timezone,
            screen = screen,
            locale = locale,
            device_locale = device_locale,
            os_version = os_version,
            app_version = app_version,
            header_user_agent = header_user_agent,
            device_name = device_name,
            chats_count = chats_count,
            interactive = interactive,
            presence_sync = presence_sync,
            chats_sync = chats_sync,
            contacts_sync = contacts_sync,
            drafts_sync = drafts_sync,
        )


    async def _login(
            self,
            token: str,
            device_id: str = get_random_device_id(),
            device_type: str = 'WEB',
            timezone: str = 'Europe/Moscow',
            screen: str = '1440x2560 1.0x',
            locale: str = 'ru',
            device_locale: str = 'ru',
            os_version: str = 'Linux',
            app_version: str = '26.2.10',
            header_user_agent: str = 'Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0',
            device_name: str = 'Firefox',
            chats_count: int = 40,
            interactive: bool = True,
            presence_sync: int = -1,
            chats_sync: int = 0,
            contacts_sync: int = 0,
            drafts_sync: int = 0,
    ):
        while True:
            try:
                await self._send_user_agent(
                    device_id=device_id,
                    device_type=device_type,
                    timezone=timezone,
                    screen=screen,
                    locale=locale,
                    device_locale=device_locale,
                    os_version=os_version,
                    app_version=app_version,
                    header_user_agent=header_user_agent,
                    device_name=device_name,
                )

                await self._send_auth_token(
                    token=token,
                    chats_count=chats_count,
                    interactive=interactive,
                    presence_sync=presence_sync,
                    chats_sync=chats_sync,
                    contacts_sync=contacts_sync,
                    drafts_sync=drafts_sync,
                )

                break
            except asyncio.CancelledError:
                await self.close()
                await self.connect()


    async def _keepalive(
            self
    ):
        try:
            while True:

                await self.protocol.running.wait()


                await asyncio.sleep(self._keepalive_ping_interval)

                self.__logger.debug('send keepalive ping...')

                pong = await self.protocol.send(method=SendKeepAlivePingMethod(), data={})

                self.__logger.debug('keepalive pong %s', await pong)


        except asyncio.CancelledError:
            self.__logger.debug('keepalive ping canceled')
            # await asyncio.sleep(self._keepalive_ping_interval // 2)
            # self._keepalive_task.cancel()


    async def _get_url_to_upload(self, count=1):
        await self.protocol.send(method=GetUrlToUploadFileMethod(
            count=count,
        ), data={})
        pass

    async def upload_file(self, data: bytes, typeof: type[BaseFile]) -> BaseFileAttachment:
        pass


    async def send_message(self, chat_id: int, text: str, attaches: list[BaseFileAttachment]):
        pass



