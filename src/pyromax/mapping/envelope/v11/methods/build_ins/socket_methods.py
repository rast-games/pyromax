from __future__ import annotations
from typing import TYPE_CHECKING, Any
from collections.abc import Callable, Coroutine
import asyncio

from ......utils import Backoff
from ......exceptions import MapperApiError
from .base import LoginBuildInMappingMethod
from ...payloads.responses import (
    StartSMSAuthResponse, TwoFactorLoginResponse, ChoiceLoginVariantResponse, MetadataResponse
)
from ...constants import DEFAULT_BACKOFF_CONFIG
from ..immutable import (
StartSMSAuthMethod, VerifySMSCodeMethod, GetUserDataMethod
)


if TYPE_CHECKING:
    from ...Mapper import Mapper


class SocketLoginBuildInMappingMethod(LoginBuildInMappingMethod):
    async def __call__(
            self,
            mapper: Mapper,
            *args: Any,
            login_backoff: Backoff | None = None,
            code_getter: Callable[..., Coroutine[Any, Any, int]] | None = None,
            sms_auth: bool = True,
            metadata: MetadataResponse | None = None,
            url_callback: Callable[[str], Coroutine[Any, Any, Any]] | None = None,
            **kwargs: Any
    ) -> ChoiceLoginVariantResponse:
        if sms_auth:
            return await self._resolve_sms_auth(
                mapper=mapper,
                code_getter=code_getter,
            )
        else:
            if metadata is None:
                raise MapperApiError('Metadata must be provided')
            await self._resolve_qr(
                mapper=mapper,
                metadata=metadata,
                url_callback=url_callback,
            )
            response = await mapper.send_raw_with_running_wait(
                method=GetUserDataMethod(
                    track_id=metadata.track_id
                ),
            )
            payload = response.payload
            user = ChoiceLoginVariantResponse(
                payload=payload,
            )
            return user

    @staticmethod
    async def _resolve_sms_auth(
            mapper: Mapper,
            code_getter: Callable[..., Coroutine[Any, Any, int]] | None = None
    ) -> ChoiceLoginVariantResponse:
        auth_type = 'START_AUTH'
        temp_token: str | None = None
        sms_backoff = Backoff(config=DEFAULT_BACKOFF_CONFIG)
        while True:
            try:
                response = await mapper.send_raw(
                    method=StartSMSAuthMethod(
                        phone=mapper.phone,
                        type=auth_type
                    ),
                    check_errors=True
                )
                auth_response = StartSMSAuthResponse(**response.payload)
                temp_token = auth_response.token

                break
            except MapperApiError as e:
                error = e.error
                match error:
                    case 'verify.code.wrong':
                        mapper.log(20, 'SMS code wrong, resending...')
                        auth_type = "RESEND"
                        continue
                    case 'error.limit.violate':
                        mapper.log(20, 'SMS limit violate')
                        raise e
                    case 'error.code.attempt.limit':
                        mapper.log(20, 'SMS code limit reached, over login')
                        raise e
                    case 'auth.request.forbidden':
                        mapper.log(20, 'SMS auth request forbidden for this transport')
                        raise e
                    case _:
                        mapper.log(20, f'Error while login with SMS code: {error}')
                        raise e

        verify_code: int | str
        password_challenge_response: TwoFactorLoginResponse | None = None
        if temp_token is None:
            raise RuntimeError('temp token not given')
        while True:
            try:
                if code_getter is not None:
                    verify_code = await code_getter()
                else:
                    verify_code = await asyncio.to_thread(input, 'Write a sms code: ')
                check_response = await mapper.send_raw(
                    method=VerifySMSCodeMethod(
                        temp_token=temp_token,
                        auth_token_type='CHECK_CODE',
                        verify_code=str(verify_code),
                    ),
                    check_errors=True
                )
                password_challenge_response = TwoFactorLoginResponse(
                    **check_response.payload
                )
                break
            except MapperApiError as e:
                mapper.log(40, f'Error while login with SMS code: {e}')
                error = e.error
                match error:
                    case 'error.limit.violate':
                        mapper.log(20, 'SMS code limit reached, over login')
                        raise e
                    case 'auth.request.forbidden':
                        mapper.log(20, 'SMS auth request forbidden for this transport')
                        raise e
                    case _:
                        mapper.log(20, f'Error while login with SMS code: {error}')
                        raise e

        if password_challenge_response is None:
            raise RuntimeError('Password challenge response not found.')

        choice = ChoiceLoginVariantResponse(payload=password_challenge_response)
        return choice