from __future__ import annotations
from typing import TYPE_CHECKING, Any


from .base import LoginBuildInMappingMethod
from ......exceptions import MapperApiError
from ..immutable import GetUserDataMethod
from ...payloads.responses import ChoiceLoginVariantResponse

if TYPE_CHECKING:
    from ...Mapper import Mapper
    from ...payloads.responses import MetadataResponse


class WebSocketLoginBuildInMappingMethod(LoginBuildInMappingMethod):
    async def __call__(
        self,
        mapper: Mapper,
        *args: Any,
        sms_auth: bool = False,
        **kwargs: Any,
    ) -> ChoiceLoginVariantResponse:
        """Execute the web socket login build in mapping MAX API method.

        :param mapper: Mapper backend or mapper instance.
        :type mapper: Mapper
        :param args: Positional arguments forwarded to the wrapped callable.
        :type args: Any
        :param sms_auth: The sms auth value.
        :type sms_auth: bool
        :param kwargs: Keyword arguments forwarded to the wrapped callable.
        :type kwargs: Any
        :returns: The resulting ChoiceLoginVariantResponse value.
        :rtype: ChoiceLoginVariantResponse
        :raises MapperApiError: If metadata not given for login.
        """
        if sms_auth:
            return await self._resolve_sms_auth(
                mapper=mapper,
            )

        metadata = await mapper.request_qr()
        if metadata is None:
            raise MapperApiError("Metadata not given for login")
        track_id = metadata.track_id
        await self._resolve_qr(mapper=mapper, metadata=metadata)

        return await mapper.confirm_qr(track_id=track_id)
