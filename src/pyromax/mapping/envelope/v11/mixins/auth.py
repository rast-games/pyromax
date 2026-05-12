from __future__ import annotations
import logging
import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, TYPE_CHECKING
import qrcode


from .....protocol.envelope import Envelope, EnvelopeProtocol
from ..payloads.models import BaseUserAgentMappingModel
from ..methods.immutable import SendUserAgentMethod, SendAuthTokenMethod, GetMetadataForLoginMethod, SendKeepAlivePingMethod, Resolve2FAMethod
from ..payloads.responses import AuthResponse, SuccessLoginResponse, MetadataResponse, ChoiceLoginVariantResponse
from .....utils import read_token, write_token, Backoff
from .....exceptions import MapperCancelledError, RestartMapperError, BaseMapperError, MapperTransportError
from ..constants import DEFAULT_BACKOFF_CONFIG

if TYPE_CHECKING:
    from .....core import MaxApi

class AuthMixin:
    _logger: logging.Logger

    send_raw: Callable[..., Coroutine[Any, Any, Envelope]]
    max_api: MaxApi
    TOKEN_NAME: str
    user_agent: BaseUserAgentMappingModel
    _resolve_two_factor: Callable[..., Coroutine[Any, Any, Any]]
    sms_auth: bool
    _call_build_in_method: Callable[..., Coroutine[Any, Any, Any]]
    _authorized: asyncio.Event
    protocol: EnvelopeProtocol
    _keepalive_ping_interval: int
    keep_alive_interactive: bool
    send: Callable[..., Coroutine[Any, Any, Envelope]]
    send_raw_with_running_wait: Callable[..., Coroutine[Any, Any, Envelope]]
    _lifecycle_manager: Any
    password: str



    async def _send_user_agent(
            self,
            user_agent: BaseUserAgentMappingModel,
    ) -> None:


        await self.send_raw(
            method=SendUserAgentMethod(
                user_agent=user_agent,
            )
        )


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
        self._logger.debug('sending auth token')
        response = await self.send_raw(method=SendAuthTokenMethod(
            token=token,
            chats_count=chats_count,
            interactive=interactive,
            presence_sync=presence_sync,
            chats_sync=chats_sync,
            contacts_sync=contacts_sync,
            drafts_sync=drafts_sync,
        ))

        self._logger.debug('recv auth token response')

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


    async def login(
            self,
            url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
            login_backoff: Backoff | None = None,
    ) -> SuccessLoginResponse | None:
        token = await read_token(
            name_of_token=self.TOKEN_NAME
        )

        if not token:

            self._logger.info('haven`t token. Start login...')
            user = await self._login(
                user_agent=self.user_agent,
                login_backoff=login_backoff,
                url_callback=url_callback,
            )

            self._logger.info('get token from login...')

            token = user.token_attrs.token
            self.token = token

            await write_token(
                token=token,
                name_of_token=self.TOKEN_NAME
            )
            self._logger.info('was write token in tokens.json successfully.')
            return user
        else:
            self._logger.info('token was get from tokens.json')
            self.token = token
            return None


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
        except MapperCancelledError:
            self._logger.error('Login cancelled')
            await login_backoff.asleep()
            raise RestartMapperError('Failed to login')
        except TimeoutError as e:
            self._logger.error('Login timed out')
            raise RestartMapperError('Failed to login - timeout')
        except Exception as e:
            self._logger.error('Failed to login: %s - %s', e.__class__.__name__, e)
            await login_backoff.asleep()
            raise RestartMapperError('Failed to login')


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
        # while True:
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
            # break
        except BaseMapperError as e:
            self._logger.warning('Cancelled auth')
            self._authorized.clear()
            self.protocol.failed.set()
            raise RestartMapperError('Auth failed') from e


    async def _keepalive(
            self
    ) -> None:
        try:
            while True:
                await asyncio.sleep(self._keepalive_ping_interval)
                self._logger.debug('send keepalive ping...')
                pong = await self.send(method=SendKeepAlivePingMethod(
                    interactive=self.keep_alive_interactive
                ),
                    return_exception=True
                )
                self._logger.debug('keepalive pong %s', pong)
        except MapperCancelledError:
            self._logger.warning('keepalive ping canceled')
        except MapperTransportError as e:
            self._logger.warning('keepalive transport error: %s', e, exc_info=True)



