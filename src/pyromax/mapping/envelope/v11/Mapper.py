from __future__ import annotations
import asyncio
import logging
import time
from asyncio import Task, Lock
from collections.abc import AsyncGenerator, Callable
from typing import Any, TYPE_CHECKING, Coroutine, Sequence, cast

import qrcode


from ....exceptions import SendMessageFileError, SendMessageNotFoundError, SendMessageError
from ...bases import BaseMapper
from ....models import BaseMaxObject, BaseFileAttachment
from ....protocol import StreamMaxProtocol, Envelope, EnvelopeProtocol
from ....utils import read_token, write_token, get_random_device_id
from .methods import SendUserAgentMethod, SendAuthTokenMethod, SendKeepAlivePingMethod, \
    GetUrlToUploadFileMethod, SendMessageMethod, GetMetadataForLoginMethod, TrackLoginMethod, GetUserDataMethod
from .payloads.responses import AuthResponse, TrackLoginResponse, MetadataResponse, SuccessLoginResponse, ResponseWithUrl
from .payloads.models import UserAgentMappingModel
from .translate.ToDTO import update_translate, upload_file, FILE_OPCODES, FALLBACK_FILE_OPCODE, BaseFileMapping
from ...registry import register_mapper
from ....dispatcher.event.UpdateType import Update

if TYPE_CHECKING:
    from .... import BaseMaxProtocol
    from ....models import MessageLink
    from ....core import MaxApi

@register_mapper('EnvelopeV11')
class Mapper(BaseMapper[EnvelopeProtocol]):

    def __init__(
            self,
            protocol: EnvelopeProtocol,
            keepalive_ping_interval: int
    ) -> None:
        self.protocol = protocol
        self._keepalive_ping_interval = keepalive_ping_interval
        self.__logger = logging.getLogger('MapperV11')
        self._keepalive_task: Task[Any] | None = None
        self._update_listener_task: Task[Any] | None = None
        self.token: str | None = None
        self.TOKEN_NAME = 'ENVELOPE_MAX_TOKEN_V11'
        self.max_api: MaxApi | None = None
        self._manage_lifecycle_task: Task[Any] | None = None
        self._update_listener_lock: Lock = Lock()


    async def _async_init(
            self,
            max_api: MaxApi,
            protocol: EnvelopeProtocol,
            *args: Any,
            keepalive_ping_interval: int = 30,
            **kwargs: Any,
    ) -> None:
        from src.pyromax import MaxApi

        if not isinstance(max_api, MaxApi):
            raise TypeError('max_api must be an instance of MaxApi')

        if not isinstance(protocol, EnvelopeProtocol):
            raise TypeError("protocol must be an instance of EnvelopeProtocol")
        await asyncio.to_thread(self.__init__, protocol=protocol, keepalive_ping_interval=keepalive_ping_interval) # type: ignore[misc]
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
            user_agent=UserAgentMappingModel(
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
    ) -> AsyncGenerator[Update, None]:
        """Endless updates reader"""
        async with self._update_listener_lock:
            while True:
                updates = await self.protocol.get_updates()
                for update in updates:
                    yield cast(Update, update_translate(update, context=context))


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
        response_future = await self.protocol.send(method=SendAuthTokenMethod(
            token=token,
            chats_count=chats_count,
            interactive=interactive,
            presence_sync=presence_sync,
            chats_sync=chats_sync,
            contacts_sync=contacts_sync,
            drafts_sync=drafts_sync,
        ))

        response = await response_future

        auth_model = AuthResponse(
            **response.payload
        )

        if self.max_api is None:
            raise RuntimeError('You try a send auth token, but not bound MaxApi instance to mapper')

        self.max_api.id = auth_model.profile.contact.id
        self.max_api.phone = str(auth_model.profile.contact.phone)
        self.max_api.names = auth_model.profile.contact.names



    async def _manage_lifecycle(
            self,
    ) -> None:
        while True:
            # debug_tasks()
            await self.protocol.failed.wait()
            await self.close()
            if self.token is None:
                raise RuntimeError('Try a connect without token')
            await self.connect()
            await self._auth(
                token = self.token
            )


    async def connect(
            self,
    ) -> None:
        await self.protocol.connect()
        if self._keepalive_task:
            self._keepalive_task.cancel()
        self._keepalive_task = asyncio.create_task(self._keepalive())


    async def close(
            self,
    ) -> None:
        await self.protocol.close()

        if self._keepalive_task:
            self._keepalive_task.cancel()


    async def initialize_client(
            self,
            token: str | None = None,
            device_id: str = get_random_device_id(),
            protocol_version: str='v11',
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
            url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
            **kwargs: Any
    ) -> None:
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
            track_id: str,
            polling_interval: int | float,
    ) -> None:

        not_logged = True
        while not_logged:
            await asyncio.sleep(polling_interval)

            response_future = await self.protocol.send(
                method=TrackLoginMethod(
                    track_id=track_id
                )
            )

            response = await response_future

            track_data = TrackLoginResponse(
                **response.payload
            )

            if track_data is None:
                raise RuntimeError('Track login failed.')

            if track_data.status is None:
                raise RuntimeError("Track status is missing in response")


            if track_data.status and track_data.status.expires_at < time.time() or track_data.error or track_data.error_message or track_data.localized_message:
                msg = '''
                Time for login expired
                    '''
                raise TimeoutError(msg)


            if track_data.status.login_available:
                not_logged = False


    async def _get_user_data(
            self,
            track_id: str
    ) -> SuccessLoginResponse:

        response_future = await self.protocol.send(
            method=GetUserDataMethod(
                track_id=track_id
            )
        )

        response = await response_future
        user = SuccessLoginResponse(
            **response.payload
        )

        if self.max_api is None:
            raise RuntimeError('Mapper not bound to MaxApi instance')

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
            url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
    ) -> SuccessLoginResponse:

        if not url_callback:
            async def url_callback(url: str) -> None:
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

        response_future = await self.protocol.send(
            method=GetMetadataForLoginMethod()
        )

        response = await response_future

        metadata = MetadataResponse(**response.payload)

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
    ) -> None:
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
    ) -> None:
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
    ) -> dict[str, Any]:
        response_future = await self.protocol.send(
            method=GetUrlToUploadFileMethod(type_of_file_opcode=opcode, count=count)
        )

        response = await response_future

        payload = ResponseWithUrl(
            **response.payload
        ).model_dump(exclude_none=True)

        return payload


    async def upload_file(
            self,
            data: bytes | None,
            typeof: type[BaseFileAttachment],
            count: int = 1,
            file_name: str | None = None,
            uploaded: bool = False,
            **kwargs: Any
    ) -> BaseFileMapping[Any]:
        payload = {}
        # if data is None:
        #     raise RuntimeError('data cannot be None')
        if not uploaded:
            payload = await self._create_cell_for_file(
                opcode=FILE_OPCODES.get(typeof, FALLBACK_FILE_OPCODE),
                count=count,
            )

        uploaded_file = await upload_file(
            data=data,
            typeof=typeof,
            file_name=file_name,
            uploaded=uploaded,
            **payload,
            **kwargs
        )

        return uploaded_file


    async def send_message( # type: ignore[override]
            self,
            chat_id: int,
            text: str | None = None,
            attaches: Sequence[BaseFileMapping[Any]] | None = None,
            elements: Any = None,
            link: MessageLink | None=None,
    ) -> None:

        if not attaches:
            attaches = []

        attachments = []

        for attach in attaches:
            attachments.extend(attach.to_payload)


        try:

            response_future = await self.protocol.send(
                method=SendMessageMethod(
                    chat_id=chat_id,
                    text=text,
                    cid=-round(time.time() * 1000),
                    attaches=attachments,
                    elements=elements,
                    link=link,
                ),
            )

            response = await response_future

            while error_if_exist := response.model_dump().get('payload', {}).get('error'):
                error_message = response.model_dump().get('payload', {}).get('message')
                title = response.model_dump().get('payload', {}).get('title')
                match error_if_exist:
                    case 'attachment.not.ready':
                        response_future = await self.protocol.send(
                            method=SendMessageMethod(
                                chat_id=chat_id,
                                text=text,
                                cid=-round(time.time() * 1000),
                                attaches=attachments,
                                elements=elements,
                                link=link,
                            ),
                        )
                        response = await response_future
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