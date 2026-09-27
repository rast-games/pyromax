from __future__ import annotations
from typing import TYPE_CHECKING, Any
import asyncio

from ......utils import Backoff
from ......exceptions import MapperApiError
from .base import LoginBuildInMappingMethod
from ...payloads.responses import ChoiceLoginVariantResponse

from ..immutable import GetUserDataMethod

if TYPE_CHECKING:
    from ...Mapper import Mapper
    from ......models import RegistrationConfig


class SocketLoginBuildInMappingMethod(LoginBuildInMappingMethod):
    async def __call__(
        self,
        mapper: Mapper,
        *args: Any,
        login_backoff: Backoff | None = None,
        sms_auth: bool = True,
        use_mobile_fingerprint: bool = True,
        registration_config: RegistrationConfig | None = None,
        **kwargs: Any,
    ) -> ChoiceLoginVariantResponse:
        """Execute the socket login build in mapping MAX API method.

        :param mapper: Mapper backend or mapper instance.
        :type mapper: Mapper
        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param login_backoff: Backoff instance to process.
        :type login_backoff: Backoff | None
        :param sms_auth: The sms auth value.
        :type sms_auth: bool
        :param use_mobile_fingerprint: Whether to use mobile fingerprint.
        :type use_mobile_fingerprint: bool
        :param registration_config: RegistrationConfig instance to process.
        :type registration_config: RegistrationConfig | None
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting ChoiceLoginVariantResponse value.
        :rtype: ChoiceLoginVariantResponse
        :raises MapperApiError: If metadata must be provided.
        """
        if sms_auth:
            return await self._resolve_sms_auth(
                mapper=mapper,
                use_mobile_fingerprint=use_mobile_fingerprint,
                registration_config=registration_config,
            )
        else:
            metadata = await mapper.request_qr()
            if metadata is None:
                raise MapperApiError("Metadata must be provided")
            await self._resolve_qr(
                mapper=mapper,
                metadata=metadata,
            )
            return await mapper.confirm_qr(track_id=metadata.track_id)
