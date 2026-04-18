from __future__ import annotations
import asyncio
import logging
import time
from asyncio import Task, Lock
from collections.abc import AsyncGenerator, Callable
from typing import Any, TYPE_CHECKING, Coroutine, Sequence, cast

import aiohttp
import qrcode

from ....protocol import BaseMaxProtocol, Envelope
from ....exceptions import SendMessageFileError, SendMessageNotFoundError, SendMessageError, DownloadFileError
from ...bases import BaseMapper
from ....models import BaseFileAttachment
from ....protocol import EnvelopeProtocol
from ....utils import read_token, write_token, get_random_device_id, Backoff, BackoffConfig, clean_and_map
from .methods import BaseMethod, SendUserAgentMethod, SendAuthTokenMethod, SendKeepAlivePingMethod, \
    GetUrlToUploadFileMethod, SendMessageMethod, GetMetadataForLoginMethod, TrackLoginMethod, GetUserDataMethod, GetFileLinkMethod
from .payloads.responses import AuthResponse, TrackLoginResponse, MetadataResponse, SuccessLoginResponse, ResponseWithUrl, SendMessageResponse
from .payloads.models import UserAgentMappingModel, BaseFileMappingModel, MessageMappingModel
from .translate.ToDTO import update_translate, upload_file, FILE_OPCODES, FALLBACK_FILE_OPCODE, BaseFileMapping, get_file_url
from ...registry import register_mapper
from ....dispatcher.event.UpdateType import Update
from ....exceptions import BackoffError

if TYPE_CHECKING:
    from ....models import MessageLink
    from ....core import MaxApi


DEFAULT_BACKOFF_CONFIG = BackoffConfig(min_delay=1.0, max_delay=5.0, factor=1.3, jitter=0.1)

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
        self._authorized = asyncio.Event()


    async def _async_init(
            self,
            max_api: MaxApi,
            protocol: EnvelopeProtocol,
            *args: Any,
            keepalive_ping_interval: int = 30,
            **kwargs: Any,
    ) -> None:
        from ....core import MaxApi


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
        await (self.__send_without_auth_check
            (method=SendUserAgentMethod(
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
        )))


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
        response = await self.__send_without_auth_check(method=SendAuthTokenMethod(
            token=token,
            chats_count=chats_count,
            interactive=interactive,
            presence_sync=presence_sync,
            chats_sync=chats_sync,
            contacts_sync=contacts_sync,
            drafts_sync=drafts_sync,
        ))

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
            self._authorized.clear()
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


    async def __send_without_auth_check(self, method: BaseMethod, data: dict[Any, Any] | None = None) -> Envelope:
        if data is None:
            data = {}
        while True:
            try:
                await self.protocol.running.wait()
                response_future = await self.protocol.send(method=method, data=data)
                response = await response_future
                return response
            except asyncio.CancelledError:
                self.protocol.running.clear()
                self.protocol.failed.set()
                self._authorized.clear()
                self.__logger.debug('Cancelled request')


    async def __send(self, method: BaseMethod, data: dict[Any, Any] | None = None) -> Envelope:
        if data is None:
            data = {}
        while True:
            try:
                await self.protocol.running.wait()
                await self._authorized.wait()
                response_future = await self.protocol.send(method=method, data=data)
                response = await response_future
                return response
            except asyncio.CancelledError:
                self.protocol.running.clear()
                self.protocol.failed.set()
                self._authorized.clear()
                self.__logger.debug('Cancelled request')


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

            response = await self.__send_without_auth_check(
                method=TrackLoginMethod(
                    track_id=track_id
                )
            )

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

        response = await self.__send_without_auth_check(
            method=GetUserDataMethod(
                track_id=track_id
            )
        )
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

        response = await self.__send_without_auth_check(
            method=GetMetadataForLoginMethod()
        )

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
                self._authorized.set()
                break
            except asyncio.CancelledError:
                self._authorized.clear()
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
                pong = await self.__send(method=SendKeepAlivePingMethod())
                self.__logger.debug('keepalive pong %s', pong)
        except asyncio.CancelledError:
            self.__logger.debug('keepalive ping canceled')


    async def _create_cell_for_file(
            self,
            opcode: int,
            count: int = 1,
    ) -> dict[str, Any]:
        response = await self.__send(
            method=GetUrlToUploadFileMethod(type_of_file_opcode=opcode, count=count)
        )

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
    ) -> list[BaseFileMappingModel]:
        payload = {}
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


    async def download_file( # type: ignore[override]
            self,
            file: BaseFileMappingModel,
            cookies_to_download: dict[str, str] | None = None,
            headers_to_download: dict[str, str] | None = None,
            **kwargs: Any
    ) -> tuple[bytes, dict[str, str]] | tuple[None, None]:
        url = await get_file_url(file=file, mapper=cast(BaseMapper[BaseMaxProtocol[Any, Any]], self), **kwargs)
        if url is None:
            self.__logger.warning('cannot get a download url for file')
            return None, None
        api = self.max_api
        if api is None:
            raise RuntimeError('max_api must be set')
        opts = api.transport_options or {}
        user_agent_header = opts.get('user_agent_header') or 'Mozilla/5.0 (X11; Linux x86_64; rv:145.0) Gecko/20100101 Firefox/145.0'

        headers: dict[str, str]
        if headers_to_download is None:
            headers = {
                "User-Agent": user_agent_header,
                "Accept": "*/*",
                "Referer": "https://ok.ru/"
            }
        else:
            headers = headers_to_download

        cookies: dict[str, str]
        if cookies_to_download is None:
            cookies = {
                "tstc": "p"
            }
        else:
            cookies = cookies_to_download
        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
            async with session.get(url=url) as response:
                if response.status > 299:
                    self.__logger.warning('Download failed for file')
                    raise DownloadFileError('Download failed for file')
                chunks = []
                async for chunk in response.content.iter_chunked(8192):
                    chunks.append(chunk)
                return b''.join(chunks), dict(response.headers)
        return None, None



    async def send_message( # type: ignore[override]
            self,
            chat_id: int,
            text: str | None = None,
            attaches: Sequence[BaseFileMappingModel] | None = None,
            link: MessageLink | None = None,
    ) -> MessageMappingModel | None:
        original_attaches = attaches
        if not attaches:
            attaches = []
        attachments = []
        for attach in attaches:
            attachments.extend(attach.to_payload)
        backoff = Backoff(config=DEFAULT_BACKOFF_CONFIG)
        text, elements = clean_and_map(
            text if text else '',
            [
                'STRONG', 'EMPHASIZED', 'UNDERLINE', 'STRIKETHROUGH', 'QUOTE', 'LINK'
            ]
        )
        try:
            response = await self.__send(
                method=SendMessageMethod(
                    chat_id=chat_id,
                    text=text,
                    cid=-round(time.time() * 1000),
                    attaches=attachments,
                    elements=elements,
                    link=link,
                ),
            )

            try:
                while error_if_exist := response.model_dump().get('payload', {}).get('error'):
                    error_message = response.model_dump().get('payload', {}).get('message')
                    title = response.model_dump().get('payload', {}).get('title')
                    match error_if_exist:
                        case 'attachment.not.ready':
                            response = await self.__send(
                                method=SendMessageMethod(
                                    chat_id=chat_id,
                                    text=text,
                                    cid=-round(time.time() * 1000),
                                    attaches=attachments,
                                    elements=elements,
                                    link=link,
                                ),
                            )
                            await backoff.asleep()
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
            except BackoffError:
                raise SendMessageError('Max attempts to send message exceeded')
            response_parsed = SendMessageResponse(
                **response.payload
            )
            for attach in response_parsed.message.attaches:
                attach.message_id = response_parsed.message.id
                attach.chat_id = response_parsed.chat_id
                attach.uploaded = True
            for i, attach in enumerate(original_attaches or []):
                recv_attach = response_parsed.message.attaches[i]
                for attr, value in recv_attach.__dict__.items():
                    setattr(attach, attr, value)
            return response_parsed.message

        except (asyncio.CancelledError, self.protocol.transport.BASE_EXCEPTION_FOR_TRANSPORT) as e:
            self.__logger.error('Error sending message: %s', e)
            return None