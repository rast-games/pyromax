from __future__ import annotations
import asyncio
import logging
import time
from asyncio import Task, Lock, CancelledError
from collections.abc import AsyncGenerator, Callable
from typing import Any, TYPE_CHECKING, Coroutine, Sequence, cast

import aiohttp
import qrcode

# from .... import BaseUserAgent
from ....protocol import BaseMaxProtocol, Envelope
from ....exceptions import SendMessageFileError, SendMessageNotFoundError, SendMessageError, DownloadFileError, RestartMapperError, \
    MapperApiError, AlreadyFailedError
from ...bases import BaseMapper
from ....models import BaseFileAttachment, BaseMaxObject
from ....protocol import EnvelopeProtocol
from ....utils import read_token, write_token, Backoff, clean_and_map
from .methods.immutable import (
    BaseMethod, SendUserAgentMethod, SendAuthTokenMethod, SendKeepAlivePingMethod, GetUrlToUploadFileMethod,
    SendMessageMethod, GetGeneralInfoAboutMember, Resolve2FAMethod, GetMetadataForLoginMethod
)
from .payloads.responses import (
    AuthResponse, MetadataResponse, SuccessLoginResponse, ResponseWithUrl, SendMessageResponse,
    GetContactResponse, ErrorMessageResponse, ChoiceLoginVariantResponse
)
from .payloads.models import BaseUserAgentMappingModel, BaseFileMappingModel, MessageMappingModel
from .translate.ToDTO import (update_translate, upload_file, FILE_OPCODES, FALLBACK_FILE_OPCODE, get_file_url,
                              translate_models)
from .payloads.shared import CamelCaseModel
from ...registry import register_mapper
from ....dispatcher.event.UpdateType import Update
from ....exceptions import BackoffError
from ....utils import debug_tasks
from .constants import DEVICE_TYPE_TO_USERAGENT_MODEL, DEFAULT_BACKOFF_CONFIG
from .methods.build_ins import build_method, method_names

if TYPE_CHECKING:
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
        self.keep_alive_interactive: bool = True
        self._update_listener_task: Task[Any] | None = None
        self.token: str | None = None
        self.TOKEN_NAME = 'ENVELOPE_MAX_TOKEN_V11' + self.protocol.transport.__class__.__name__
        self.max_api: MaxApi | None = None
        self._manage_lifecycle_task: Task[Any] | None = None
        self._update_listener_lock: Lock = Lock()
        self._authorized = asyncio.Event()
        self.user_agent: BaseUserAgentMappingModel | None = None
        self.logged: bool = False
        self.password: str | None = None
        self.phone = None
        self.sms_auth = False


    @property
    def DEVICE_TYPE_TO_USERAGENT_MODEL(self) -> dict[str, type[BaseUserAgentMappingModel]]:
        return DEVICE_TYPE_TO_USERAGENT_MODEL


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
        self.max_api = max_api


    async def _call_build_in_method(
            self,
            method_name: method_names,
            *args: Any,
            **kwargs: Any,
    ):
        method = build_method(method_name=method_name, transport=self.protocol.transport)
        return await method(mapper=self,*args, **kwargs)

    async def _send_user_agent(
            self,
            user_agent: BaseUserAgentMappingModel,
    ) -> None:


        await self.send_raw(
            method=SendUserAgentMethod(
                user_agent=user_agent,
            )
        )


    async def listen_updates(
            self,
            context: Any,
    ) -> AsyncGenerator[Update, None]:
        """Endless updates reader"""
        async with self._update_listener_lock:
            while True:
                updates = await self.protocol.get_updates()
                for update in updates:
                    if update.model_dump().get('error'):
                        error = ErrorMessageResponse(**update.model_dump(by_alias=True))
                        error_msg = \
                            f"""
                            error: {error.error},
                            title: {error.title},
                            localized_message: {error.localized_message},
                            message: {error.message}
                            """
                        raise MapperApiError(error_msg)
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
        self.__logger.debug('sending auth token')
        response = await self.send_raw(method=SendAuthTokenMethod(
            token=token,
            chats_count=chats_count,
            interactive=interactive,
            presence_sync=presence_sync,
            chats_sync=chats_sync,
            contacts_sync=contacts_sync,
            drafts_sync=drafts_sync,
        ))

        self.__logger.debug('recv auth token response')

        auth_model = AuthResponse(
            **response.payload
        )

        if self.max_api is None:
            raise RuntimeError('You try a send auth token, but not bound MaxApi instance to mapper')

        self.max_api.id = auth_model.profile.contact.id
        self.max_api.phone = str(auth_model.profile.contact.phone)
        # names = [translate_models(name).model_dump() for name in auth_model.profile.contact.names]
        # self.max_api.names = names
        self.max_api.names = auth_model.profile.contact.names



    async def _manage_lifecycle(
            self,
            **kwargs
    ) -> None:
        while True:
            manage_lifecycle_backoff = Backoff(DEFAULT_BACKOFF_CONFIG)
            try:
                self.__logger.debug('closing protocol')
                await self.close()
                self.__logger.debug('protocol closed')
                self._authorized.clear()
                await self.connect()
                if not self.logged or not self.token:
                    await self.login(kwargs.get('url_callback'), login_backoff=manage_lifecycle_backoff)
                    self.logged = True
                await self._auth(
                    token=self.token,
                    user_agent=self.user_agent
                )
                self.__logger.debug('auth token sent')
                await self.protocol.failed.wait()
                self.__logger.warning('catch protocol failed')

                if self.token is None:
                    raise RuntimeError('Try a connect without token')

                self.__logger.debug('protocol connected')

            except (RestartMapperError, AlreadyFailedError, BackoffError) as e:
                self.__logger.warning('Start/restart error: %s', e)
                self.__logger.debug('Failed to start/restart mapper')
                self.__logger.debug('starting/restarting mapper(again)...')




    async def connect(
            self,
    ) -> None:
        await self.protocol.connect()
        self.__logger.debug('protocol connected')
        if self._keepalive_task:
            self.__logger.debug('have another keepalive task, cancel it')
            self._keepalive_task.cancel()
            self.__logger.debug('keepalive task cancelled')
        self.__logger.debug('start keepalive task')
        self._keepalive_task = asyncio.create_task(self._keepalive())
        self.__logger.debug('keepalive task started')


    async def close(
            self,
    ) -> None:
        await self.protocol.close()

        if self._keepalive_task:
            self._keepalive_task.cancel()


    def log(self, level: int, msg: str) -> None:
        """
        CRITICAL = 50
        FATAL = CRITICAL
        ERROR = 40
        WARNING = 30
        WARN = WARNING
        INFO = 20
        DEBUG = 10
        NOTSET = 0

        :param level:
        :param msg:
        :return:
        """
        self.__logger.log(level, msg)

    async def send_raw(self, method: BaseMethod, data: dict[Any, Any] | None = None, check_errors: bool = False) -> Envelope:
        """Send request without catching exceptions"""
        if data is None:
            data = {}

        if self.protocol.failed.is_set():
            raise AlreadyFailedError('Mapper protocol already failed, need restart')

        response_future = await self.protocol.send(
            method=method,
            data=data,
        )
        response = await response_future
        if check_errors and response.payload.get('error'):
            print('RAISING ERROR AJF :ASJK F:LASJF')
            error = ErrorMessageResponse(**response.payload)
            error_msg = \
            f"""
            error: {error.error},
            title: {error.title},
            localized_message: {error.localized_message},
            message: {error.error_message}
            
            """
            error_obj = MapperApiError(error_msg)
            error_obj.title = error.title
            error_obj.localized_message = error.localized_message
            error_obj.message = error.error_message
            error_obj.error = error.error
            raise error_obj
        return response



    async def send_raw_with_running_wait(self, method: BaseMethod, data: dict[Any, Any] | None = None) -> Envelope:
        if data is None:
            data = {}
        await self.protocol.running.wait()
        response = await self.send_raw(method=method, data=data)
        return response


    async def send(self, method: BaseMethod, data: dict[Any, Any] | None = None, return_exception: bool = False) -> Envelope:
        if data is None:
            data = {}
        while True:
            try:
                await self.protocol.running.wait()
                await self._authorized.wait()
                response = await self.send_raw(method=method, data=data)
                return response
            except CancelledError:
                await self.protocol.close()
                self._authorized.clear()
                self.__logger.warning('Cancelled request')
                if return_exception:
                    raise CancelledError('Cancelled request')


    async def login(
            self,
            url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
            login_backoff: Backoff | None = None,
    ) -> SuccessLoginResponse | None:
        token = await read_token(
            name_of_token=self.TOKEN_NAME
        )

        if not token:

            self.__logger.info('haven`t token. Start login...')
            user = await self._login(
                user_agent=self.user_agent,
                login_backoff=login_backoff,
                url_callback=url_callback,
            )

            self.__logger.info('get token from login...')

            token = user.token_attrs.token
            self.token = token

            await write_token(
                token=token,
                name_of_token=self.TOKEN_NAME
            )
            self.__logger.info('was write token in tokens.json successfully.')
            return user
        else:
            self.__logger.info('token was get from tokens.json')
            self.token = token
            return None

    async def initialize_client(
            self,
            token: str | None = None,
            device_id: str | None = None,
            protocol_version: str='v11',
            device_type: str = 'WEB',
            password: str | None = None,
            phone: str | None = None,
            sms_auth=False,
            interactive: bool = True,
            url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
            **kwargs: Any
    ) -> None:
        if device_type not in self.DEVICE_TYPE_TO_USERAGENT_MODEL:
            raise RuntimeError(f'Unknown device type: {device_type}')
        user_agent_model = self.DEVICE_TYPE_TO_USERAGENT_MODEL[device_type]
        user_agent = user_agent_model(device_type=device_type)
        self.user_agent = user_agent
        self.token = token
        self.password = password
        self.phone = phone
        self.sms_auth = sms_auth
        self._manage_lifecycle_task = asyncio.create_task(self._manage_lifecycle(url_callback=url_callback))
        self.__logger.info("Mapper initialized")


    async def _resolve_two_factor(
            self,
            track_id: str
    ) -> SuccessLoginResponse:
        if self.password is None:
            raise RuntimeError('No password given, but need 2FA')
        response = await self.send_raw_with_running_wait(
            method=Resolve2FAMethod(
                password=self.password,
                track_id=track_id,
            )
        )
        user = SuccessLoginResponse(
            **response.payload
        )
        return user


    async def _login(
            self,
            user_agent: BaseUserAgentMappingModel,
            login_backoff: Backoff | None = None,
            code_getter = None,
            url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
    ) -> SuccessLoginResponse:
        if login_backoff is None:
            login_backoff = Backoff(config=DEFAULT_BACKOFF_CONFIG)
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

        try:
            await self._send_user_agent(
                user_agent = user_agent,
            )
            response = await self.send_raw(
                method=GetMetadataForLoginMethod(),
                check_errors=True
            )
            metadata = MetadataResponse(**response.payload)

            choice: ChoiceLoginVariantResponse = await self._call_build_in_method(
                method_name='LOGIN',
                metadata=metadata,
                url_callback=url_callback,
                code_getter=code_getter,
                login_backoff=login_backoff,
                user_agent=user_agent,
                sms_auth=self.sms_auth,
            )
            user: SuccessLoginResponse

            if choice.payload.TwoFactor:
                user = await self._resolve_two_factor(
                    track_id=choice.payload.password_challenge.track_id
                )
            else:
                user = choice.payload

            return user
        except asyncio.CancelledError:
            self.__logger.error('Login cancelled')
            await login_backoff.asleep()
            raise RestartMapperError('Failed to login')
        except TimeoutError as e:
            self.__logger.error('Login timed out')
            raise RestartMapperError('Failed to login - timeout')
        except Exception as e:
            self.__logger.error('Failed to login: %s - %s', e.__class__.__name__, e)
            await login_backoff.asleep()
            raise RestartMapperError('Failed to login')

    async def _auth(
            self,
            token: str,
            user_agent: BaseUserAgentMappingModel,
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
                    user_agent = user_agent,
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
                self.__logger.warning('Cancelled auth')
                self._authorized.clear()
                self.protocol.failed.set()
                raise RestartMapperError('Auth failed')


    async def _keepalive(
            self
    ) -> None:
        try:
            while True:
                await self.protocol.running.wait()
                await asyncio.sleep(self._keepalive_ping_interval)
                self.__logger.debug('send keepalive ping...')
                pong = await self.send(method=SendKeepAlivePingMethod(
                    interactive=self.keep_alive_interactive
                ))
                self.__logger.debug('keepalive pong %s', pong)
        except asyncio.CancelledError:
            self.__logger.warning('keepalive ping canceled')


    async def _create_cell_for_file(
            self,
            opcode: int,
            count: int = 1,
    ) -> dict[str, Any]:
        response = await self.send(
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
            if hasattr(attach, 'is_attach') and attach.is_attach:
                attachments.extend(attach.to_payload)
        backoff = Backoff(config=DEFAULT_BACKOFF_CONFIG)
        text, elements = clean_and_map(
            text if text else '',
            [
                'STRONG', 'EMPHASIZED', 'UNDERLINE', 'STRIKETHROUGH', 'QUOTE', 'LINK'
            ]
        )
        try:
            response = await self.send(
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
                            response = await self.send(
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
                if hasattr(attach, 'is_attach') and attach.is_attach and hasattr(attach, 'is_downloadable') and attach.is_downloadable:
                    recv_attach = response_parsed.message.attaches[i]
                    for attr, value in recv_attach.__dict__.items():
                        setattr(attach, attr, value)
            return response_parsed.message

        except (asyncio.CancelledError, self.protocol.transport.BASE_EXCEPTION_FOR_TRANSPORT) as e:
            self.__logger.error('Error sending message: %s', e)
            return None

    async def get_member_by_id(self, member_id: int | list[int]) -> Sequence[BaseMaxObject | CamelCaseModel]:
        contact_ids: list[int]
        if isinstance(member_id, int):
            contact_ids = [member_id]
        elif isinstance(member_id, list):
            contact_ids = member_id
        else:
            raise TypeError('member_id must be int or list[int]')

        response_envelope = await self.send(
            method=GetGeneralInfoAboutMember(
                contact_ids=contact_ids,
            )
        )

        response = GetContactResponse(
            **response_envelope.payload
        )


        contacts = [translate_models(mapping_contact) for mapping_contact in response.contacts]

        return cast(list[BaseMaxObject], contacts)




