from __future__ import annotations
import asyncio
import logging
import time
from asyncio import Task, Lock
from collections.abc import AsyncGenerator
from typing import Any, TYPE_CHECKING, Coroutine

import qrcode

from ....exceptions import SendMessageFileError, SendMessageNotFoundError, SendMessageError
from ...bases import BaseMapper
from ....models import BaseMaxObject, BaseFileAttachment
from ....protocol import StreamMaxProtocol, Envelope, EnvelopeProtocol
from ....utils import read_token, write_token
from ....utils import debug_tasks
from ....utils import get_random_device_id
from .methods import SendUserAgentMethod, SendAuthTokenMethod, SendKeepAlivePingMethod, \
    GetUrlToUploadFileMethod, SendMessageMethod, GetMetadataForLogin, TrackLogin, GetUserData
from .payloads import UserAgentModel, PayloadWithUrlModel, AuthResponseModel, MetadataPayloadModel, \
    TrackLoginResponseModel, SuccessLoginModel
from .translate import translate, upload_file, FILE_OPCODES, FALLBACK_FILE_OPCODE, BaseFile
from ...registry import register_mapper

if TYPE_CHECKING:
    from src.pyromax import MaxApi

@register_mapper('EnvelopeV11')
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
        self.TOKEN_NAME = 'ENVELOPE_MAX_TOKEN_V11'
        self.max_api: MaxApi | None = None
        self._manage_lifecycle_task: None | Task = None
        self._update_listener_lock: Lock = Lock()


    async def _async_init(
            self,
            max_api: MaxApi,
            protocol: EnvelopeProtocol,
            *args,
            keepalive_ping_interval: int = 30,
            **kwargs,
    ):
        from src.pyromax import MaxApi

        if not isinstance(max_api, MaxApi):
            raise TypeError('max_api must be an instance of MaxApi')

        if not isinstance(protocol, StreamMaxProtocol):
            raise TypeError("protocol must be an instance of BaseMaxProtocol")
        await asyncio.to_thread(self.__init__, protocol=protocol, keepalive_ping_interval=keepalive_ping_interval)
        await self.connect()
        self._manage_lifecycle_task = asyncio.create_task(self._manage_lifecycle())
        self.__logger.info("Mapper initialized")
        self.max_api = max_api


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
        ))


    async def listen_updates(
            self,
            context: Any,
    ) -> AsyncGenerator[BaseMaxObject, None]:
        """Endless updates reader"""
        async with self._update_listener_lock:
            while True:
                updates = await self.protocol.get_updates()
                for update in updates:
                    yield translate(update, context=context)


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
        response = await self.protocol.send(method=SendAuthTokenMethod(
            token=token,
            chats_count=chats_count,
            interactive=interactive,
            presence_sync=presence_sync,
            chats_sync=chats_sync,
            contacts_sync=contacts_sync,
            drafts_sync=drafts_sync,
        ))

        response = await response

        auth_model = AuthResponseModel(
            **response.payload
        )

        self.max_api.id = auth_model.profile.contact.id
        self.max_api.phone = str(auth_model.profile.contact.phone)
        self.max_api.names = auth_model.profile.contact.names



    async def _manage_lifecycle(
            self,
    ):
        while True:
            # debug_tasks()
            await self.protocol.failed.wait()
            await self.close()
            await self.connect()
            await self._auth(
                token = self.token
            )


    async def connect(
            self,
    ):
        await self.protocol.connect()
        if self._keepalive_task:
            self._keepalive_task.cancel()
        self._keepalive_task = asyncio.create_task(self._keepalive())


    async def close(
            self,
    ):
        await self.protocol.close()

        if self._keepalive_task:
            self._keepalive_task.cancel()


    async def initialize_client(
            self,
            token: str = None,
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
            url_callback = None
    ):
        if not token:

            token = await read_token(
                name_of_token=self.TOKEN_NAME
            )

            if not token:

                self.__logger.info('haven`t token. Start login...')
                user = await self._login(
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
                    url_callback=url_callback,
                )

                self.__logger.info('get token from login...')

                token = user.token_attrs.token

                await write_token(
                    token=token,
                    name_of_token=self.TOKEN_NAME
                )
                self.__logger.info('was write token in tokens.json successfully.')
            else:
                self.__logger.info('token was get from tokens.json')

        self.token = token

        await self._auth(
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


    async def _track_login(
            self,
            track_id,
            polling_interval,
    ):

        not_logged = True
        while not_logged:
            await asyncio.sleep(polling_interval)

            response = await self.protocol.send(
                method=TrackLogin(
                    track_id=track_id
                )
            )

            response = await response

            track_data = TrackLoginResponseModel(
                **response.payload
            )

            if track_data.status and track_data.status.expires_at < time.time() or track_data.error or track_data.error_message or track_data.localized_message:
                msg = f'''
                Time for login expired
                    '''
                raise TimeoutError(msg)


            if track_data.status.login_available == True:
                not_logged = False


    async def _get_user_data(
            self,
            track_id
    ) -> SuccessLoginModel:

        response = await self.protocol.send(
            method=GetUserData(
                track_id=track_id
            )
        )

        response = await response
        user = SuccessLoginModel(
            **response.payload
        )

        self.max_api.token = self.token = user.token_attrs.token


        return user

    async def _login(
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
            url_callback: Coroutine = None,
    ) -> SuccessLoginModel:

        if not url_callback:
            async def url_callback(url: str):
                """
                Creating a QR code scanned by max. It is displayed immediately in the console

                Args:
                    url - authorization url

                """

                qr = qrcode.QRCode()
                qr.add_data(url)

                qr.make(fit=True)
                qr.print_ascii(invert=True)

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

        response = await self.protocol.send(
            method=GetMetadataForLogin()
        )

        response = await response

        metadata = MetadataPayloadModel(**response.payload)

        await url_callback(metadata.qr_link)

        await self._track_login(
            polling_interval=metadata.polling_interval,
            track_id=metadata.track_id,
        )

        user = await self._get_user_data(
            track_id=metadata.track_id,
        )

        return user


    async def _auth(
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
                pong = await self.protocol.send(method=SendKeepAlivePingMethod())
                self.__logger.debug('keepalive pong %s', await pong)
        except asyncio.CancelledError:
            self.__logger.debug('keepalive ping canceled')


    async def _create_cell_for_file(
            self,
            opcode: int,
            count: int = 1,
    ):
        response = await self.protocol.send(
            method=GetUrlToUploadFileMethod(type_of_file_opcode=opcode, count=count)
        )

        return await response


    async def upload_file(self, data: bytes, typeof: type[BaseFileAttachment], count = 1, file_name: str = None, uploaded: bool = False, **kwargs) -> BaseFileAttachment:


        payload = {}
        if not uploaded:
            response: Envelope = await self._create_cell_for_file(
                opcode=FILE_OPCODES.get(typeof, FALLBACK_FILE_OPCODE),
                count=count,
            )

            payload = PayloadWithUrlModel(
                **response.payload
            ).model_dump(exclude_none=True)

        uploaded_file = await upload_file(
            data=data,
            typeof=typeof,
            file_name=file_name,
            uploaded=uploaded,
            **payload,
            **kwargs
        )

        return uploaded_file


    async def send_message(
            self,
            chat_id: int,
            text: str = None,
            attaches: list[BaseFile] = None,
            elements=None,
            link=None,
    ):

        if not attaches:
            attaches = []

        attachments = []

        for attach in attaches:
            attachments.extend(attach.to_payload)


        try:

            response = await self.protocol.send(
                method=SendMessageMethod(
                    chat_id=chat_id,
                    text=text,
                    cid=-round(time.time() * 1000),
                    attaches=attachments,
                    elements=elements,
                    link=link,
                ),
            )

            response: Envelope = await response

            while error_if_exist := response.model_dump().get('payload').get('error'):
                error_message = response.model_dump().get('payload').get('message')
                title = response.model_dump().get('payload').get('title')
                match error_if_exist:
                    case 'attachment.not.ready':
                        response = await self.protocol.send(
                            method=SendMessageMethod(
                                chat_id=chat_id,
                                text=text,
                                cid=-round(time.time() * 1000),
                                attaches=attachments,
                                elements=elements,
                                link=link,
                            ),
                        )
                        response: Envelope = await response
                        continue
                    case 'proto.payload':
                        raise SendMessageFileError(
                            f'''
                            title: {title},
                            error: {error_if_exist},
                            message: {error_message}
                            '''
                        )
                    case 'not.found':
                        raise SendMessageNotFoundError(
                            f'''
                            title: {title},
                            error: {error_if_exist},
                            message: {error_message}
                            '''
                        )
                    case _:
                        raise SendMessageError(
                            f'''
                            title: {title},
                            error: {error_if_exist},
                            message: {error_message}
                            '''
                        )



        except (asyncio.CancelledError, self.protocol.transport.BASE_EXCEPTION_FOR_TRANSPORT) as e:
            self.__logger.error('Error sending message: %s', e)