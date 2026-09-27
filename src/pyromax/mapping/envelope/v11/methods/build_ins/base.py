from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any
# from ..immutable import (
#     TrackLoginMethod,
#     GetMetadataForLoginMethod,
#     StartSMSAuthMethod,
#     VerifySMSCodeMethod,
# )
from ......exceptions import MapperApiError
from ...payloads.responses import (
    MetadataResponse,
    ChoiceLoginVariantResponse,
    SuccessLoginResponse,
)
from ......utils import Backoff

if TYPE_CHECKING:
    from ...Mapper import Mapper
    from ......models import RegistrationConfig


class BaseBuildInMappingMethod(ABC):
    @abstractmethod
    async def __call__(self, mapper: Mapper, *args: Any, **kwargs: Any) -> Any:
        """Execute the base build in mapping MAX API method.

        :param mapper: Mapper backend or mapper instance.
        :type mapper: Mapper
        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The value returned by the wrapped callable or backend.
        :rtype: Any
        """
        pass


class LoginBuildInMappingMethod(BaseBuildInMappingMethod):
    @abstractmethod
    async def __call__(
        self,
        mapper: Mapper,
        *args: Any,
        login_backoff: Backoff | None = None,
        **kwargs: Any,
    ) -> ChoiceLoginVariantResponse:
        """Execute the login build in mapping MAX API method.

        :param mapper: Mapper backend or mapper instance.
        :type mapper: Mapper
        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param login_backoff: Backoff instance to process.
        :type login_backoff: Backoff | None
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting ChoiceLoginVariantResponse value.
        :rtype: ChoiceLoginVariantResponse
        """
        pass

    @staticmethod
    async def _track_login(
        mapper: Mapper,
        metadata: MetadataResponse,
    ) -> None:
        """Track login.

        :param mapper: Mapper backend or mapper instance.
        :type mapper: Mapper
        :param metadata: MetadataResponse instance to process.
        :type metadata: MetadataResponse
        :raises RuntimeError: If track login failed.
        :raises RuntimeError: If track status is missing in response.
        :raises TimeoutError: If the requested action cannot be completed.
        """
        track_id = metadata.track_id
        polling_interval = metadata.polling_interval
        expires_at = metadata.expires_at

        while time.time() < expires_at:
            await asyncio.sleep(polling_interval)

            track_data = await mapper.check_qr(track_id=track_id)

            if track_data is None:
                raise RuntimeError("Track login failed.")

            if track_data.status is None:
                raise RuntimeError("Track status is missing in response")

            if track_data.status.login_available:
                return None

            if (
                track_data.status
                and track_data.status.expires_at < time.time()
                or track_data.error
                or track_data.error_message
                or track_data.localized_message
            ):
                msg = """
                Time for login expired
                    """
                raise TimeoutError(msg)

    async def _resolve_qr(
        self,
        mapper: Mapper,
        metadata: MetadataResponse,
    ) -> None:
        """Resolve qr.

        :param mapper: Mapper backend or mapper instance.
        :type mapper: Mapper
        :param metadata: MetadataResponse instance to process.
        :type metadata: MetadataResponse
        """
        url = metadata.qr_link
        await mapper.auth_interactor.show_qr(url)

        await self._track_login(
            mapper=mapper,
            metadata=metadata,
        )

    @staticmethod
    async def _end_registration(
        mapper: Mapper,
        registration_config: RegistrationConfig,
        choice: ChoiceLoginVariantResponse,
    ) -> ChoiceLoginVariantResponse:
        """End registration.

        :param mapper: Mapper backend or mapper instance.
        :type mapper: Mapper
        :param registration_config: RegistrationConfig instance to process.
        :type registration_config: RegistrationConfig
        :param choice: ChoiceLoginVariantResponse instance to process.
        :type choice: ChoiceLoginVariantResponse
        :returns: The resulting ChoiceLoginVariantResponse value.
        :rtype: ChoiceLoginVariantResponse
        :raises MapperApiError: If try a register already registered account.
        """
        if choice.payload.token_attrs.register_token is None:
            raise MapperApiError("Try a register already registered account.")
        response = await mapper.confirm_registration(
            token=choice.payload.token_attrs.register_token,
            first_name=registration_config.first_name,
            last_name=registration_config.last_name,
        )
        choice.payload.token_attrs.token = response.token
        return choice

    async def _resolve_sms_auth(
        self,
        mapper: Mapper,
        use_mobile_fingerprint: bool = True,
        registration_config: RegistrationConfig | None = None,
    ) -> ChoiceLoginVariantResponse:
        """Resolve sms auth.

        :param mapper: Mapper backend or mapper instance.
        :type mapper: Mapper
        :param use_mobile_fingerprint: Whether to use mobile fingerprint.
        :type use_mobile_fingerprint: bool
        :param registration_config: RegistrationConfig instance to process.
        :type registration_config: RegistrationConfig | None
        :returns: The resulting ChoiceLoginVariantResponse value.
        :rtype: ChoiceLoginVariantResponse
        :raises RuntimeError: If phone is required to use sms auth.
        :raises MapperApiError: If sMS auth send code limit reached.
        :raises RuntimeError: If temp token not given.
        :raises MapperApiError: If registration config not given, cannot end registration for account.
        """
        auth_type = {"auth_type": "START_AUTH"}
        # temp_token: str | None = None
        # sms_backoff = Backoff(config=DEFAULT_BACKOFF_CONFIG)
        if mapper.phone is None:
            raise RuntimeError("Phone is required to use sms auth.")

        for _ in range(5):
            try:

                auth_response = await mapper.request_code(
                    auth_type=auth_type["auth_type"],
                    phone=mapper.phone,
                    use_mobile_fingerprint=use_mobile_fingerprint,
                )
                temp_token = auth_response.token

                verify_code: int | str
                if temp_token is None:
                    raise RuntimeError("temp token not given")

                wrong_attempts = 4
                while True:
                    try:
                        verify_code = await mapper.auth_interactor.request_sms_code(
                            mapper.phone
                        )
                        choice = await mapper.send_code(
                            token=temp_token,
                            verify_code=str(verify_code),
                            auth_token_type="CHECK_CODE",
                        )
                        if (
                            isinstance(choice.payload, SuccessLoginResponse)
                            and choice.payload.token_attrs.register_token
                        ):
                            if registration_config is None:
                                raise MapperApiError(
                                    "Registration config not given, cannot end registration for account"
                                )
                            return await self._end_registration(
                                mapper, registration_config, choice
                            )

                        return choice
                    except MapperApiError as e:
                        mapper.log(40, f"Error while login with SMS code: {e}")
                        error = e.error
                        # await sms_backoff.asleep()
                        match error:
                            case "verify.code.wrong":
                                if wrong_attempts == 0:
                                    raise e
                                wrong_attempts -= 1
                                mapper.log(20, "SMS code wrong, try again...")
                                continue

                            case "error.limit.violate":
                                mapper.log(20, "SMS code limit reached, over login")
                                raise e
                            case "auth.request.forbidden":
                                mapper.log(
                                    20, "SMS auth request forbidden for this transport"
                                )
                                raise e
                            case _:
                                mapper.log(
                                    20, f"Error while login with SMS code: {error}"
                                )
                                raise e
            except MapperApiError as e:
                error = e.error
                match error:
                    case "verify.code.wrong":
                        mapper.log(20, "SMS code wrong, resending...")
                        auth_type["auth_type"] = "RESEND"
                        continue
                    case "error.limit.violate":
                        mapper.log(20, "SMS limit violate")
                        raise e
                    case "error.code.attempt.limit":
                        mapper.log(20, "SMS code limit reached, over login")
                        raise e
                    case "auth.request.forbidden":
                        mapper.log(20, "SMS auth request forbidden for this transport")
                        raise e
                    case _:
                        mapper.log(20, f"Error while login with SMS code: {error}")
                        continue
        else:
            raise MapperApiError("SMS auth send code limit reached.")
